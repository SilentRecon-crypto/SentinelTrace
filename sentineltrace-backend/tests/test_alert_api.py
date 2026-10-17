import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.alert import Alert  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_MULE_ACCOUNT_ID = 3722


def _ensure_risk_exists(client):
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")


# ---------------------------------------------------------------
# API — valid / missing complaint / precondition
# ---------------------------------------------------------------
def test_generate_alerts_valid_complaint(client):
    _ensure_risk_exists(client)
    resp = client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["complaint_id"] == TEST_COMPLAINT_ID
    assert len(body["results"]) >= 1
    top = next(r for r in body["results"] if r["account_id"] == KNOWN_MULE_ACCOUNT_ID)
    assert top["severity"] == "critical"
    assert 0.0 <= top["risk_priority_value"] <= 1.0
    assert 0.0 <= top["priority_score"] <= 1.0


def test_generate_alerts_nonexistent_complaint_returns_404(client):
    resp = client.post("/api/v1/complaints/99999999/alerts/generate")
    assert resp.status_code == 404


def test_generate_alerts_without_risk_returns_409(client):
    db = SessionLocal()
    try:
        from app.models.complaint import Complaint
        from app.models.risk import RiskScore
        risked_ids = {r.complaint_id for r in db.query(RiskScore.complaint_id).all()}
        candidate = db.query(Complaint).filter(~Complaint.complaint_id.in_(risked_ids)).first()
    finally:
        db.close()
    if candidate is None:
        return  # every complaint already risk-scored this session; nothing to assert
    resp = client.post(f"/api/v1/complaints/{candidate.complaint_id}/alerts/generate")
    assert resp.status_code == 409


def test_get_alerts_nonexistent_complaint_returns_404(client):
    """404 must be reserved for a complaint that genuinely doesn't exist —
    not for 'complaint exists but has zero persisted alerts' (see the two
    tests below, added by the Stage 5 static audit fix)."""
    resp = client.get("/api/v1/complaints/99999999/alerts")
    assert resp.status_code == 404


def test_get_alerts_for_existing_complaint_never_generated_returns_200_not_404(client):
    """STAGE 5 STATIC AUDIT FIX regression test: a complaint that exists but
    has never had POST .../alerts/generate called on it (or that legitimately
    generated zero alerts) must return 200 with an empty/whatever list, never
    a 404 implying something failed."""
    db = SessionLocal()
    try:
        from app.models.complaint import Complaint
        alerted_ids = {a.complaint_id for a in db.query(Alert.complaint_id).all()}
        candidate = db.query(Complaint).filter(~Complaint.complaint_id.in_(alerted_ids)).first()
    finally:
        db.close()
    if candidate is None:
        return  # every complaint already has alerts this session; nothing to assert
    resp = client.get(f"/api/v1/complaints/{candidate.complaint_id}/alerts")
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_get_alerts_returns_200_empty_list_when_zero_alerts_legitimately_generated(client):
    """STAGE 5 STATIC AUDIT FIX regression test: force a real zero-trigger
    generation (via config, restored afterward) and confirm both POST and
    the subsequent GET return 200 with an empty list rather than 404 —
    proving the API no longer conflates 'never generated' with 'generated,
    zero qualifying alerts'."""
    import app.core.alert_config as cfg

    _ensure_risk_exists(client)
    original_levels = cfg.ALERT_TRIGGERING_PRIORITY_LEVELS
    cfg.ALERT_TRIGGERING_PRIORITY_LEVELS = []  # nothing can trigger
    try:
        post_resp = client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
        assert post_resp.status_code == 200
        assert post_resp.json()["results"] == []

        get_resp = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts")
        assert get_resp.status_code == 200
        assert get_resp.json()["results"] == []
    finally:
        cfg.ALERT_TRIGGERING_PRIORITY_LEVELS = original_levels
        # restore real alerts for TEST_COMPLAINT_ID so later tests in this
        # session see the normal, expected state again
        client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")


def test_get_alert_queue(client):
    _ensure_risk_exists(client)
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
    resp = client.get("/api/v1/alerts/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert "results" in body


def test_alert_queue_is_deterministically_ordered(client):
    _ensure_risk_exists(client)
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
    resp = client.get("/api/v1/alerts/queue")
    results = resp.json()["results"]
    scores = [(r["priority_score"], r["risk_priority_value"], r["rank"]) for r in results]
    assert scores == sorted(scores, key=lambda t: (-t[0], -t[1], t[2]))


# ---------------------------------------------------------------
# Persistence / idempotency
# ---------------------------------------------------------------
def test_generate_alerts_persists_and_get_matches(client):
    _ensure_risk_exists(client)
    post_body = client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate").json()
    get_body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts").json()
    post_by_account = {r["account_id"]: r["alert_type"] for r in post_body["results"]}
    get_by_account = {r["account_id"]: r["alert_type"] for r in get_body["results"]}
    assert post_by_account == get_by_account


def test_repeated_generate_is_idempotent_no_accumulation(client):
    _ensure_risk_exists(client)
    counts = []
    for _ in range(3):
        client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
        db = SessionLocal()
        try:
            counts.append(db.query(Alert).filter(Alert.complaint_id == TEST_COMPLAINT_ID).count())
        finally:
            db.close()
    assert counts[0] == counts[1] == counts[2]


# ---------------------------------------------------------------
# Database integrity
# ---------------------------------------------------------------
def test_no_orphan_alerts(client):
    _ensure_risk_exists(client)
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
    db = SessionLocal()
    try:
        from app.models.account import Account
        from app.models.complaint import Complaint
        from app.models.risk import RiskScore
        rows = db.query(Alert).all()
        complaint_ids = {c.complaint_id for c in db.query(Complaint.complaint_id).all()}
        account_ids = {a.account_id for a in db.query(Account.account_id).all()}
        risk_score_ids = {r.score_id for r in db.query(RiskScore.score_id).all()}
        for r in rows:
            assert r.complaint_id in complaint_ids
            assert r.account_id in account_ids
            assert r.risk_score_id in risk_score_ids
    finally:
        db.close()


def test_no_duplicate_logical_alerts(client):
    _ensure_risk_exists(client)
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
    db = SessionLocal()
    try:
        rows = db.query(Alert).filter(Alert.complaint_id == TEST_COMPLAINT_ID).all()
        keys = [(r.complaint_id, r.account_id, r.alert_type) for r in rows]
    finally:
        db.close()
    assert len(keys) == len(set(keys))


def test_canonical_stage1_counts_unchanged_after_stage5(client):
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
def test_alert_responses_contain_no_ground_truth(client):
    _ensure_risk_exists(client)
    generate_body = client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate").json()
    get_body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts").json()
    queue_body = client.get("/api/v1/alerts/queue").json()
    for body in (generate_body, get_body, queue_body):
        s = str(body)
        for forbidden in ('"chain"', '"label"', '"account_type"', "legit_low", "legit_high", "confusor", "adversarial_bait"):
            assert forbidden not in s


# ---------------------------------------------------------------
# Stage 4 regression (must remain unchanged by Stage 5 presence)
# ---------------------------------------------------------------
def test_stage4_risk_and_intervention_unaffected_by_alert_generation(client):
    _ensure_risk_exists(client)
    risk_before = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk").json()
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
    risk_after = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk").json()
    intervention_after = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/intervention-window").json()
    assert risk_before["results"] == risk_after["results"]
    assert intervention_after["method"] == "synthetic_historical_hop_timing"
    assert intervention_after["validation_status"] == "synthetic_demo_only"
