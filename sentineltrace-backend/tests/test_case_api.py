import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core import case_config as cfg  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.alert import Alert  # noqa: E402
from app.models.case import Case, CaseNote  # noqa: E402
from app.services import case_engine  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_MULE_ACCOUNT_ID = 3722


def _ensure_alert_exists(client):
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")


def _get_top_alert_id(client) -> str:
    resp = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts")
    body = resp.json()
    top = next(r for r in body["results"] if r["account_id"] == KNOWN_MULE_ACCOUNT_ID)
    return top["alert_id"]


# ---------------------------------------------------------------
# Config sanity
# ---------------------------------------------------------------
def test_case_status_default_is_valid():
    assert cfg.CASE_STATUS_DEFAULT in cfg.CASE_VALID_STATUSES


def test_resolved_status_is_terminal():
    assert cfg.CASE_STATUS_TRANSITIONS[cfg.CASE_STATUS_RESOLVED] == []


def test_every_status_reachable_via_some_transition_or_is_default():
    reachable = {cfg.CASE_STATUS_DEFAULT}
    for targets in cfg.CASE_STATUS_TRANSITIONS.values():
        reachable.update(targets)
    assert reachable == set(cfg.CASE_VALID_STATUSES)


# ---------------------------------------------------------------
# Case creation
# ---------------------------------------------------------------
def test_open_case_for_valid_alert(client):
    _ensure_alert_exists(client)
    alert_id = _get_top_alert_id(client)
    resp = client.post(f"/api/v1/alerts/{alert_id}/cases")
    assert resp.status_code == 201
    body = resp.json()
    assert body["alert_id"] == alert_id
    assert body["complaint_id"] == TEST_COMPLAINT_ID
    assert body["account_id"] == KNOWN_MULE_ACCOUNT_ID
    assert body["status"] == cfg.CASE_STATUS_DEFAULT
    assert body["assigned_to"] is None


def test_open_case_for_nonexistent_alert_returns_404(client):
    import uuid
    resp = client.post(f"/api/v1/alerts/{uuid.uuid4()}/cases")
    assert resp.status_code == 404


def test_open_duplicate_case_for_same_alert_returns_409(client):
    _ensure_alert_exists(client)
    alert_id = _get_top_alert_id(client)
    db = SessionLocal()
    try:
        existing = db.query(Case).filter(Case.alert_id == alert_id).first()
    finally:
        db.close()
    if existing is None:
        client.post(f"/api/v1/alerts/{alert_id}/cases")
    resp = client.post(f"/api/v1/alerts/{alert_id}/cases")
    assert resp.status_code == 409
    assert "detail" in resp.json()


# ---------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------
def _get_or_create_case_id(client) -> str:
    alert_id = _get_top_alert_id(client)
    db = SessionLocal()
    try:
        existing = db.query(Case).filter(Case.alert_id == alert_id).first()
        if existing is not None:
            return str(existing.case_id)
    finally:
        db.close()
    resp = client.post(f"/api/v1/alerts/{alert_id}/cases")
    return resp.json()["case_id"]


def test_legal_transition_open_to_investigating(client):
    _ensure_alert_exists(client)
    case_id = _get_or_create_case_id(client)
    resp = client.patch(f"/api/v1/cases/{case_id}", json={"status": "open"})  # ensure known baseline is allowed (no-op if already open)
    resp = client.get(f"/api/v1/cases/{case_id}")
    if resp.json()["status"] == cfg.CASE_STATUS_OPEN:
        resp = client.patch(f"/api/v1/cases/{case_id}", json={"status": cfg.CASE_STATUS_INVESTIGATING})
        assert resp.status_code == 200
        assert resp.json()["status"] == cfg.CASE_STATUS_INVESTIGATING


def test_illegal_transition_rejected(client):
    """resolved is terminal — attempting any transition out of it must 409,
    never silently succeed."""
    _ensure_alert_exists(client)
    case_id = _get_or_create_case_id(client)
    # Drive to resolved via a legal path from whatever state it's currently in.
    current = client.get(f"/api/v1/cases/{case_id}").json()["status"]
    path = {
        cfg.CASE_STATUS_OPEN: [cfg.CASE_STATUS_INVESTIGATING, cfg.CASE_STATUS_RESOLVED],
        cfg.CASE_STATUS_INVESTIGATING: [cfg.CASE_STATUS_RESOLVED],
        cfg.CASE_STATUS_ESCALATED: [cfg.CASE_STATUS_RESOLVED],
        cfg.CASE_STATUS_RESOLVED: [],
    }[current]
    for step in path:
        r = client.patch(f"/api/v1/cases/{case_id}", json={"status": step})
        assert r.status_code == 200

    resp = client.patch(f"/api/v1/cases/{case_id}", json={"status": cfg.CASE_STATUS_OPEN})
    assert resp.status_code == 409

    # Confirm the illegal attempt did NOT mutate the case.
    after = client.get(f"/api/v1/cases/{case_id}").json()
    assert after["status"] == cfg.CASE_STATUS_RESOLVED


def test_invalid_status_value_returns_422(client):
    _ensure_alert_exists(client)
    case_id = _get_or_create_case_id(client)
    resp = client.patch(f"/api/v1/cases/{case_id}", json={"status": "not_a_real_status"})
    assert resp.status_code == 422


def test_update_nonexistent_case_returns_404(client):
    import uuid
    resp = client.patch(f"/api/v1/cases/{uuid.uuid4()}", json={"status": cfg.CASE_STATUS_INVESTIGATING})
    assert resp.status_code == 404


# ---------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------
def test_assign_case_to_investigator(client):
    _ensure_alert_exists(client)
    case_id = _get_or_create_case_id(client)
    resp = client.patch(f"/api/v1/cases/{case_id}", json={"assigned_to": "investigator_42"})
    assert resp.status_code == 200
    assert resp.json()["assigned_to"] == "investigator_42"


def test_clear_assignment_explicitly(client):
    _ensure_alert_exists(client)
    case_id = _get_or_create_case_id(client)
    client.patch(f"/api/v1/cases/{case_id}", json={"assigned_to": "investigator_42"})
    resp = client.patch(f"/api/v1/cases/{case_id}", json={"assigned_to": None})
    assert resp.status_code == 200
    assert resp.json()["assigned_to"] is None


def test_omitting_assigned_to_leaves_it_unchanged(client):
    _ensure_alert_exists(client)
    case_id = _get_or_create_case_id(client)
    client.patch(f"/api/v1/cases/{case_id}", json={"assigned_to": "investigator_99"})
    resp = client.patch(f"/api/v1/cases/{case_id}", json={})  # no assigned_to key at all
    assert resp.status_code == 200
    assert resp.json()["assigned_to"] == "investigator_99"


# ---------------------------------------------------------------
# Notes
# ---------------------------------------------------------------
def test_add_and_retrieve_notes(client):
    _ensure_alert_exists(client)
    case_id = _get_or_create_case_id(client)
    resp = client.post(f"/api/v1/cases/{case_id}/notes", json={"author": "investigator_1", "note_text": "Reviewed transaction history, looks consistent with mule behavior."})
    assert resp.status_code == 201
    get_resp = client.get(f"/api/v1/cases/{case_id}/notes")
    assert get_resp.status_code == 200
    notes = get_resp.json()["results"]
    assert any(n["note_text"].startswith("Reviewed transaction history") for n in notes)


def test_notes_ordered_chronologically(client):
    _ensure_alert_exists(client)
    case_id = _get_or_create_case_id(client)
    client.post(f"/api/v1/cases/{case_id}/notes", json={"author": "a", "note_text": "first"})
    client.post(f"/api/v1/cases/{case_id}/notes", json={"author": "b", "note_text": "second"})
    notes = client.get(f"/api/v1/cases/{case_id}/notes").json()["results"]
    timestamps = [n["created_at"] for n in notes]
    assert timestamps == sorted(timestamps)


def test_add_note_to_nonexistent_case_returns_404(client):
    import uuid
    resp = client.post(f"/api/v1/cases/{uuid.uuid4()}/notes", json={"author": "x", "note_text": "y"})
    assert resp.status_code == 404


# ---------------------------------------------------------------
# Case queue
# ---------------------------------------------------------------
def test_case_queue_returns_200(client):
    _ensure_alert_exists(client)
    _get_or_create_case_id(client)
    resp = client.get("/api/v1/cases")
    assert resp.status_code == 200
    assert "results" in resp.json()


def test_case_queue_ordering_prioritizes_open_states_over_resolved(client):
    """NOTE: because every test in this file drives Stage 4/5 regeneration
    (which cascades to delete any existing case), at most one case exists
    at a time in this suite, so this assertion is only a weak, vacuously-
    true-for-length<=1 check of the sort call itself, not a true multi-case
    ordering proof. See the Stage 6 final report's 'known limitations'."""
    resp = client.get("/api/v1/cases")
    result_ranks = [cfg.CASE_STATUS_QUEUE_RANK.get(c["status"], 99) for c in resp.json()["results"]]
    assert result_ranks == sorted(result_ranks)


# ---------------------------------------------------------------
# Leakage protection (source-level, AST-based per Stage 5 audit fix)
# ---------------------------------------------------------------
def test_case_modules_never_read_forbidden_fields():
    import ast
    forbidden_names = {"chain", "label", "acc_type"}
    for path in ("app/services/case_engine.py", "app/api/cases.py", "app/models/case.py"):
        source = (BACKEND_ROOT / path).read_text()
        tree = ast.parse(source)
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in forbidden_names:
                violations.append((path, "attribute", node.attr, node.lineno))
            elif isinstance(node, ast.Subscript):
                sl = node.slice
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str) and sl.value in forbidden_names:
                    violations.append((path, "subscript", sl.value, node.lineno))
            elif isinstance(node, ast.keyword) and node.arg in forbidden_names:
                violations.append((path, "keyword", node.arg, node.lineno))
        assert not violations, violations


def test_case_response_contains_no_ground_truth(client):
    _ensure_alert_exists(client)
    case_id = _get_or_create_case_id(client)
    body = client.get(f"/api/v1/cases/{case_id}").json()
    s = str(body)
    for forbidden in ('"chain"', '"label"', '"account_type"', "legit_low", "legit_high", "confusor", "adversarial_bait", "mule\""):
        assert forbidden not in s


# ---------------------------------------------------------------
# DB integrity
# ---------------------------------------------------------------
def test_no_orphan_cases_or_notes(client):
    _ensure_alert_exists(client)
    _get_or_create_case_id(client)
    db = SessionLocal()
    try:
        alert_ids = {a.alert_id for a in db.query(Alert.alert_id).all()}
        case_ids = {c.case_id for c in db.query(Case.case_id).all()}
        for c in db.query(Case).all():
            assert c.alert_id in alert_ids
        for n in db.query(CaseNote).all():
            assert n.case_id in case_ids
    finally:
        db.close()


def test_one_case_per_alert_enforced_at_db_level(client):
    _ensure_alert_exists(client)
    alert_id = _get_top_alert_id(client)
    db = SessionLocal()
    try:
        count = db.query(Case).filter(Case.alert_id == alert_id).count()
    finally:
        db.close()
    assert count <= 1


# ---------------------------------------------------------------
# Stage 1-5 regression (must remain unaffected by Stage 6)
# ---------------------------------------------------------------
def test_canonical_stage1_counts_unchanged_after_stage6(client):
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


def test_stage5_alerts_unaffected_by_case_creation(client):
    _ensure_alert_exists(client)
    before = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts").json()
    _get_or_create_case_id(client)
    after = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts").json()
    assert before == after


def test_alert_deletion_cascades_to_case(client):
    """Regenerating alerts for a complaint deletes+reinserts Alert rows
    (Stage 5's documented 'replace current' behavior), which — via
    ON DELETE CASCADE — also removes any Case built on the now-superseded
    alert. This is a deliberate consistency choice inherited from Stage 5,
    verified here rather than assumed."""
    _ensure_alert_exists(client)
    alert_id = _get_top_alert_id(client)
    case_resp = client.post(f"/api/v1/alerts/{alert_id}/cases")
    case_id = case_resp.json()["case_id"] if case_resp.status_code == 201 else None
    if case_id is None:
        db = SessionLocal()
        try:
            existing = db.query(Case).filter(Case.alert_id == alert_id).first()
            case_id = str(existing.case_id) if existing else None
        finally:
            db.close()
    assert case_id is not None

    # Force Stage 4 risk regeneration -> cascades to alerts -> cascades to case.
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")

    import uuid as uuid_mod
    db = SessionLocal()
    try:
        still_exists = db.get(Case, uuid_mod.UUID(case_id))
    finally:
        db.close()
    # After cascade, the old case row must be gone (not orphaned).
    assert still_exists is None

    # Restore a normal alert+case state for any later tests in the session.
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
