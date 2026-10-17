import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.intervention import InterventionWindowRecord  # noqa: E402
from app.models.risk import RiskScore  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_MULE_ACCOUNT_ID = 3722


def _ensure_prediction_exists(client):
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})


# ---------------------------------------------------------------
# API — valid / missing complaint
# ---------------------------------------------------------------
def test_post_risk_valid_complaint(client):
    _ensure_prediction_exists(client)
    resp = client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")
    assert resp.status_code == 200
    body = resp.json()
    assert body["complaint_id"] == TEST_COMPLAINT_ID
    assert len(body["results"]) == 5
    top = next(r for r in body["results"] if r["account_id"] == KNOWN_MULE_ACCOUNT_ID)
    assert top["ml_score"] == 0.9969592777671326  # Model A output must be exactly unchanged


def test_post_risk_nonexistent_complaint_returns_404(client):
    resp = client.post("/api/v1/complaints/99999999/risk")
    assert resp.status_code == 404


def test_post_risk_without_prediction_returns_409(client):
    db = SessionLocal()
    try:
        from app.models.complaint import Complaint
        from app.models.prediction import MuleChainPrediction
        predicted_ids = {p.complaint_id for p in db.query(MuleChainPrediction).all()}
        candidate = db.query(Complaint).filter(~Complaint.complaint_id.in_(predicted_ids)).first()
    finally:
        db.close()
    if candidate is None:
        return  # every complaint already predicted this session; nothing to assert
    resp = client.post(f"/api/v1/complaints/{candidate.complaint_id}/risk")
    assert resp.status_code == 409


def test_get_risk_before_any_post_returns_404_for_unpredicted_complaint(client):
    resp = client.get("/api/v1/complaints/99999999/risk")
    assert resp.status_code == 404


def test_get_intervention_window_valid(client):
    _ensure_prediction_exists(client)
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")
    resp = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/intervention-window")
    assert resp.status_code == 200
    body = resp.json()
    assert body["complaint_id"] == TEST_COMPLAINT_ID
    assert body["account_id"] == KNOWN_MULE_ACCOUNT_ID
    assert body["validation_status"] == "synthetic_demo_only"
    assert body["method"] == "synthetic_historical_hop_timing"


def test_get_intervention_window_missing_returns_404(client):
    resp = client.get("/api/v1/complaints/99999999/intervention-window")
    assert resp.status_code == 404


# ---------------------------------------------------------------
# Persistence / idempotency
# ---------------------------------------------------------------
def test_post_risk_persists_and_get_matches(client):
    _ensure_prediction_exists(client)
    post_body = client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk").json()
    get_body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk").json()
    post_by_account = {r["account_id"]: r["priority"] for r in post_body["results"]}
    get_by_account = {r["account_id"]: r["priority"] for r in get_body["results"]}
    assert post_by_account == get_by_account


def test_repeated_post_risk_is_idempotent_no_accumulation(client):
    _ensure_prediction_exists(client)
    for _ in range(3):
        client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")

    db = SessionLocal()
    try:
        risk_count = db.query(RiskScore).filter(RiskScore.complaint_id == TEST_COMPLAINT_ID).count()
        intervention_count = db.query(InterventionWindowRecord).filter(InterventionWindowRecord.complaint_id == TEST_COMPLAINT_ID).count()
    finally:
        db.close()
    assert risk_count == 5  # top_k from the underlying prediction, never accumulates
    assert intervention_count == 1  # exactly one current window, never accumulates


# ---------------------------------------------------------------
# Database integrity
# ---------------------------------------------------------------
def test_no_orphan_risk_scores(client):
    _ensure_prediction_exists(client)
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")
    db = SessionLocal()
    try:
        from app.models.account import Account
        from app.models.complaint import Complaint
        rows = db.query(RiskScore).all()
        complaint_ids = {c.complaint_id for c in db.query(Complaint.complaint_id).all()}
        account_ids = {a.account_id for a in db.query(Account.account_id).all()}
        for r in rows:
            assert r.complaint_id in complaint_ids
            assert r.account_id in account_ids
    finally:
        db.close()


def test_no_orphan_intervention_windows(client):
    _ensure_prediction_exists(client)
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")
    db = SessionLocal()
    try:
        from app.models.account import Account
        from app.models.complaint import Complaint
        rows = db.query(InterventionWindowRecord).all()
        complaint_ids = {c.complaint_id for c in db.query(Complaint.complaint_id).all()}
        account_ids = {a.account_id for a in db.query(Account.account_id).all()}
        for r in rows:
            assert r.complaint_id in complaint_ids
            assert r.account_id in account_ids
    finally:
        db.close()


def test_canonical_stage1_counts_unchanged(client):
    """Stage 4 must never touch the Stage 1 canonical dataset."""
    db = SessionLocal()
    try:
        from app.models.account import Account
        from app.models.complaint import Complaint
        from app.models.transaction import Transaction
        assert db.query(Account).count() == 4025
        assert db.query(Transaction).count() == 38830
        assert db.query(Complaint).count() == 500
    finally:
        db.close()


# ---------------------------------------------------------------
# Response never leaks ground truth
# ---------------------------------------------------------------
def test_risk_and_intervention_responses_contain_no_ground_truth(client):
    _ensure_prediction_exists(client)
    risk_body = client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk").json()
    intervention_body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/intervention-window").json()
    for body in (risk_body, intervention_body):
        s = str(body)
        for forbidden in ('"chain"', '"label"', '"account_type"', "legit_low", "legit_high", "confusor", "adversarial_bait"):
            assert forbidden not in s
