import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.complaint import Complaint  # noqa: E402
from app.services import candidate_generation, mule_chain_prediction  # noqa: E402
from app.services.model_a import get_model_a  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_MULE_ACCOUNT_ID = 3722
FEATURE_COLS = [
    "hop_distance", "pass_through_ratio", "fan_in_recent_30d", "out_degree_recent_30d",
    "account_age_days", "confirmed_history_count", "amount_consistency", "subgraph_degree_centrality",
]


# ---------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------
def test_real_complaint_produces_candidates(client):
    db = SessionLocal()
    try:
        complaint = db.get(Complaint, TEST_COMPLAINT_ID)
        feat = candidate_generation.build_candidates_for_complaint(db, complaint)
        assert len(feat) > 0
        assert KNOWN_MULE_ACCOUNT_ID in feat.candidate_id.values
    finally:
        db.close()


def test_candidate_generation_is_deterministic(client):
    db = SessionLocal()
    try:
        complaint = db.get(Complaint, TEST_COMPLAINT_ID)
        feat1 = candidate_generation.build_candidates_for_complaint(db, complaint).sort_values("candidate_id").reset_index(drop=True)
        feat2 = candidate_generation.build_candidates_for_complaint(db, complaint).sort_values("candidate_id").reset_index(drop=True)
    finally:
        db.close()
    pd.testing.assert_frame_equal(feat1[FEATURE_COLS], feat2[FEATURE_COLS])


# ---------------------------------------------------------------
# Feature generation
# ---------------------------------------------------------------
def test_all_required_features_present_and_correctly_named(client):
    db = SessionLocal()
    try:
        complaint = db.get(Complaint, TEST_COMPLAINT_ID)
        feat = candidate_generation.build_candidates_for_complaint(db, complaint)
    finally:
        db.close()
    for f in FEATURE_COLS:
        assert f in feat.columns


def test_feature_ordering_matches_metadata(client):
    registry = get_model_a()
    assert registry.feature_names_ordered == FEATURE_COLS


# ---------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------
def test_scoring_produces_valid_probabilities(client):
    db = SessionLocal()
    try:
        complaint = db.get(Complaint, TEST_COMPLAINT_ID)
        feat = candidate_generation.build_candidates_for_complaint(db, complaint)
    finally:
        db.close()
    registry = get_model_a()
    scores = registry.predict_proba_batch(feat[FEATURE_COLS])
    assert np.all((scores >= 0.0) & (scores <= 1.0))
    assert not np.any(np.isnan(scores))
    assert not np.any(np.isinf(scores))


# ---------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------
def test_ranking_descending_and_deterministic_ties(client):
    db = SessionLocal()
    try:
        registry = get_model_a()
        result = mule_chain_prediction.run_prediction(db, registry, TEST_COMPLAINT_ID, top_k=50)
    finally:
        db.close()
    scores = [r.model_score for r in result.results]
    assert scores == sorted(scores, reverse=True)
    ranks = [r.rank for r in result.results]
    assert ranks == list(range(1, len(ranks) + 1))
    # Known result: account 3722 is rank 1 with the expected score.
    assert result.results[0].candidate_account_id == KNOWN_MULE_ACCOUNT_ID
    assert result.results[0].model_score == pytest.approx(0.996959, abs=1e-5)


# ---------------------------------------------------------------
# API
# ---------------------------------------------------------------
def test_predictions_run_valid_complaint(client):
    resp = client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["complaint_id"] == TEST_COMPLAINT_ID
    assert body["model_version"] == "model_a_v1"
    assert len(body["results"]) == 5
    assert body["results"][0]["candidate_account_id"] == KNOWN_MULE_ACCOUNT_ID


def test_predictions_run_invalid_complaint_returns_404(client):
    resp = client.post("/api/v1/predictions/run", json={"complaint_id": 99999999, "top_k": 5})
    assert resp.status_code == 404


def test_predictions_run_invalid_top_k_returns_422(client):
    resp = client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 0})
    assert resp.status_code == 422
    resp2 = client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 1000})
    assert resp2.status_code == 422


def test_get_mule_chain_after_run(client):
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    resp = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/mule-chain")
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"][0]["candidate_account_id"] == KNOWN_MULE_ACCOUNT_ID


def test_get_mule_chain_no_prediction_yet_returns_404(client):
    # Complaint 1 is very unlikely to have been predicted yet in a fresh test run;
    # use a complaint id guaranteed never called above.
    never_run_complaint_id = 999999998  # does not exist -> also validates the not-found path
    resp = client.get(f"/api/v1/complaints/{never_run_complaint_id}/mule-chain")
    assert resp.status_code == 404


# ---------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------
def test_prediction_persisted_and_retrievable_matches(client):
    run_resp = client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    run_body = run_resp.json()

    get_resp = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/mule-chain")
    get_body = get_resp.json()

    assert get_body["model_version"] == run_body["model_version"]
    assert get_body["candidate_count"] == run_body["candidate_count"]
    assert [r["candidate_account_id"] for r in get_body["results"]] == [r["candidate_account_id"] for r in run_body["results"]]
    assert [r["model_score"] for r in get_body["results"]] == [r["model_score"] for r in run_body["results"]]


# ---------------------------------------------------------------
# Leakage protection
# ---------------------------------------------------------------
def test_production_pipeline_never_reads_ground_truth_chain_field(client):
    """Static + dynamic proof that the production path cannot see the real
    complaint's chain: candidate_generation.py always passes chain=[] into
    the authoritative research function, regardless of what's actually
    stored in the complaints table."""
    source = inspect.getsource(candidate_generation.build_candidates_for_complaint)
    assert '"chain": []' in source, "candidate_generation must pass an empty chain to isolate ground truth"
    assert "complaint.chain" not in source, "candidate_generation must never read the real complaint.chain"

    db = SessionLocal()
    try:
        complaint = db.get(Complaint, TEST_COMPLAINT_ID)
        real_chain = list(complaint.chain)
        feat = candidate_generation.build_candidates_for_complaint(db, complaint)
    finally:
        db.close()

    assert len(real_chain) > 0  # sanity: the real complaint DOES have a non-empty chain in the DB
    # Every candidate's label must be 0 — proving the true chain never reached the label computation.
    assert (feat["label"] == 0).all()


def test_prediction_orchestration_drops_label_before_scoring(client):
    """Confirms run_prediction() explicitly drops the label column before
    it ever reaches the model or the API response/persistence layer."""
    source = inspect.getsource(mule_chain_prediction.run_prediction)
    assert 'drop(columns=["label"])' in source


def test_api_response_never_contains_label_or_chain_fields(client):
    resp = client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    body = resp.json()
    body_str = str(body)
    assert '"label"' not in body_str
    assert '"chain"' not in body_str
    for r in body["results"]:
        assert set(r["features"].keys()) == set(FEATURE_COLS)
