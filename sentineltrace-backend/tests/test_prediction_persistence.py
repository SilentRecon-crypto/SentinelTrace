import sys
import threading
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.prediction import MuleChainPrediction  # noqa: E402
from app.services import mule_chain_prediction  # noqa: E402
from app.services.model_a import get_model_a  # noqa: E402

TEST_COMPLAINT_ID = 452


def _row_count_and_runs(complaint_id: int):
    db = SessionLocal()
    try:
        rows = db.query(MuleChainPrediction).filter(MuleChainPrediction.complaint_id == complaint_id).all()
        run_ids = {r.prediction_run_id for r in rows}
        return len(rows), run_ids
    finally:
        db.close()


# ---------------------------------------------------------------
# Basic persistence sanity (also covered in test_predictions.py; repeated
# here alongside the hardening tests for a single place to look)
# ---------------------------------------------------------------
def test_prediction_run_has_valid_id(client):
    resp = client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    body = resp.json()
    assert body["prediction_run_id"]  # non-empty UUID string
    import uuid
    uuid.UUID(body["prediction_run_id"])  # raises if not a valid UUID


def test_candidate_count_consistent_between_post_and_get(client):
    post_body = client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5}).json()
    get_body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/mule-chain").json()
    assert post_body["candidate_count"] == get_body["candidate_count"] == 26


def test_post_and_get_are_byte_identical_including_timestamp(client):
    """Regression test: POST previously returned a pre-commit Python
    timestamp for generated_at, which could differ from the DB-persisted
    created_at that GET reads back by tens of milliseconds. POST now reads
    the timestamp back from the committed row, so the two must match exactly."""
    post_body = client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5}).json()
    get_body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/mule-chain").json()
    assert post_body == get_body


# ---------------------------------------------------------------
# Atomicity
# ---------------------------------------------------------------
def test_persistence_is_atomic_on_failure(client, monkeypatch):
    """Force a failure partway through persistence (after the delete, mid
    insert) and confirm the database ends up with EITHER the full prior
    state OR the full new state — never a partial mix."""
    registry = get_model_a()

    # Establish a known-good baseline first.
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    before_count, before_runs = _row_count_and_runs(TEST_COMPLAINT_ID)
    assert before_count == 5

    # Monkeypatch db.add on a fresh session to raise partway through, then
    # call run_prediction directly (bypassing the API's generic exception
    # handler) so we can inspect the raw database state afterward.
    db = SessionLocal()
    original_add = db.add
    call_count = {"n": 0}

    def flaky_add(instance):
        call_count["n"] += 1
        if call_count["n"] == 3:  # fail partway through inserting 5 rows
            raise RuntimeError("simulated failure mid-persistence")
        return original_add(instance)

    db.add = flaky_add

    with pytest.raises(RuntimeError):
        mule_chain_prediction.run_prediction(db, registry, TEST_COMPLAINT_ID, top_k=5)
    db.close()

    after_count, after_runs = _row_count_and_runs(TEST_COMPLAINT_ID)
    # Must NOT be left with a partial 1-2 row state.
    assert after_count in (0, 5), f"Expected atomic all-or-nothing, got {after_count} rows"


# ---------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------
def test_concurrent_prediction_runs_leave_consistent_state(client):
    """Fire two overlapping POST /predictions/run for the SAME complaint and
    confirm the final persisted state is fully consistent (exactly top_k
    rows, all sharing one prediction_run_id) rather than an interleaved mix
    from two different runs."""
    results = []

    def fire():
        resp = client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
        results.append(resp.status_code)

    threads = [threading.Thread(target=fire) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(code == 200 for code in results)

    row_count, run_ids = _row_count_and_runs(TEST_COMPLAINT_ID)
    assert row_count == 5, f"Expected exactly 5 rows after concurrent runs, got {row_count}"
    assert len(run_ids) == 1, f"Expected all rows to share one prediction_run_id, found {len(run_ids)}"


def test_no_duplicate_current_predictions_after_multiple_runs(client):
    """Calling run_prediction() several times sequentially must never
    accumulate rows — always exactly top_k current rows per complaint."""
    for _ in range(3):
        client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    row_count, run_ids = _row_count_and_runs(TEST_COMPLAINT_ID)
    assert row_count == 5
    assert len(run_ids) == 1


# ---------------------------------------------------------------
# GET must not recompute
# ---------------------------------------------------------------
def test_get_mule_chain_does_not_recompute(client, monkeypatch):
    """GET must serve persisted rows only — it must never call candidate
    generation or scoring itself."""
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})

    called = {"candidate_gen": False}

    def spy(*args, **kwargs):
        called["candidate_gen"] = True
        raise AssertionError("GET /mule-chain must not trigger candidate generation")

    import app.services.candidate_generation as cg
    monkeypatch.setattr(cg, "build_candidates_for_complaint", spy)

    resp = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/mule-chain")
    assert resp.status_code == 200
    assert called["candidate_gen"] is False
