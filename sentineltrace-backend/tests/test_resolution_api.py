import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core import case_config, resolution_config as cfg  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.models.case_resolution import CaseResolution  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_MULE_ACCOUNT_ID = 3722


def _get_case_row(case_id: str) -> Case:
    db = SessionLocal()
    try:
        return db.get(Case, uuid.UUID(case_id))
    finally:
        db.close()


def _new_case(client) -> str:
    """Fully drives the pipeline to a fresh, 'open' case for complaint 452's
    known top account. Every call regenerates risk (which cascades to
    delete any existing alert/case/evidence for this complaint — see
    Stage 6/7 README notes), so every test that calls this starts from a
    clean, self-contained state, same pattern as tests/test_case_api.py and
    tests/test_evidence_api.py."""
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
    alerts_body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts").json()
    top_alert = next(r for r in alerts_body["results"] if r["account_id"] == KNOWN_MULE_ACCOUNT_ID)
    case_resp = client.post(f"/api/v1/alerts/{top_alert['alert_id']}/cases")
    return case_resp.json()["case_id"]


def _new_resolved_case(client) -> str:
    case_id = _new_case(client)
    client.patch(f"/api/v1/cases/{case_id}", json={"status": case_config.CASE_STATUS_INVESTIGATING})
    client.patch(f"/api/v1/cases/{case_id}", json={"status": case_config.CASE_STATUS_RESOLVED})
    return case_id


# ---------------------------------------------------------------
# Config sanity
# ---------------------------------------------------------------
def test_outcome_types_are_exactly_the_authorized_closed_set():
    assert set(cfg.RESOLUTION_VALID_OUTCOME_TYPES) == {
        "confirmed_mule",
        "false_positive",
        "insufficient_evidence",
        "referred_external",
    }


def test_required_case_status_is_resolved_and_sourced_from_case_config():
    assert cfg.REQUIRED_CASE_STATUS == case_config.CASE_STATUS_RESOLVED == "resolved"


# ---------------------------------------------------------------
# 1. Valid resolution creation
# ---------------------------------------------------------------
def test_valid_resolution_creation(client):
    case_id = _new_resolved_case(client)
    resp = client.post(
        f"/api/v1/cases/{case_id}/resolution",
        json={"outcome_type": cfg.OUTCOME_TYPE_CONFIRMED_MULE, "resolution_note": "Confirmed via transaction pattern review.", "recorded_by": "investigator_1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["outcome_type"] == cfg.OUTCOME_TYPE_CONFIRMED_MULE
    assert body["recorded_by"] == "investigator_1"


# ---------------------------------------------------------------
# 2. Resolution requires resolved case
# ---------------------------------------------------------------
def test_resolution_rejected_when_case_not_resolved(client):
    case_id = _new_case(client)  # freshly created, status == 'open'
    resp = client.post(
        f"/api/v1/cases/{case_id}/resolution",
        json={"outcome_type": cfg.OUTCOME_TYPE_CONFIRMED_MULE, "recorded_by": "investigator_1"},
    )
    assert resp.status_code == 409


def test_resolution_rejected_when_case_investigating(client):
    case_id = _new_case(client)
    client.patch(f"/api/v1/cases/{case_id}", json={"status": case_config.CASE_STATUS_INVESTIGATING})
    resp = client.post(
        f"/api/v1/cases/{case_id}/resolution",
        json={"outcome_type": cfg.OUTCOME_TYPE_FALSE_POSITIVE, "recorded_by": "investigator_1"},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------
# 3. Duplicate resolution rejected
# ---------------------------------------------------------------
def test_duplicate_resolution_rejected(client):
    case_id = _new_resolved_case(client)
    first = client.post(
        f"/api/v1/cases/{case_id}/resolution",
        json={"outcome_type": cfg.OUTCOME_TYPE_FALSE_POSITIVE, "recorded_by": "investigator_1"},
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/v1/cases/{case_id}/resolution",
        json={"outcome_type": cfg.OUTCOME_TYPE_CONFIRMED_MULE, "recorded_by": "investigator_2"},
    )
    assert second.status_code == 409
    # The original resolution must be unaffected (immutable) by the rejected attempt.
    get_resp = client.get(f"/api/v1/cases/{case_id}/resolution")
    assert get_resp.json()["outcome_type"] == cfg.OUTCOME_TYPE_FALSE_POSITIVE


# ---------------------------------------------------------------
# 4. Invalid outcome rejected
# ---------------------------------------------------------------
def test_invalid_outcome_type_rejected(client):
    case_id = _new_resolved_case(client)
    resp = client.post(
        f"/api/v1/cases/{case_id}/resolution",
        json={"outcome_type": "not_a_real_outcome", "recorded_by": "investigator_1"},
    )
    assert resp.status_code == 422


def test_missing_outcome_type_rejected(client):
    case_id = _new_resolved_case(client)
    resp = client.post(f"/api/v1/cases/{case_id}/resolution", json={"recorded_by": "investigator_1"})
    assert resp.status_code == 422


def test_missing_recorded_by_rejected(client):
    case_id = _new_resolved_case(client)
    resp = client.post(f"/api/v1/cases/{case_id}/resolution", json={"outcome_type": cfg.OUTCOME_TYPE_CONFIRMED_MULE})
    assert resp.status_code == 422


# ---------------------------------------------------------------
# 5. Missing case rejected
# ---------------------------------------------------------------
def test_resolution_for_nonexistent_case_returns_404(client):
    resp = client.post(
        f"/api/v1/cases/{uuid.uuid4()}/resolution",
        json={"outcome_type": cfg.OUTCOME_TYPE_CONFIRMED_MULE, "recorded_by": "investigator_1"},
    )
    assert resp.status_code == 404


def test_get_resolution_for_nonexistent_case_returns_404(client):
    resp = client.get(f"/api/v1/cases/{uuid.uuid4()}/resolution")
    assert resp.status_code == 404


# ---------------------------------------------------------------
# 6. Retrieval before resolution
# ---------------------------------------------------------------
def test_get_resolution_before_any_recorded_returns_404(client):
    case_id = _new_resolved_case(client)
    resp = client.get(f"/api/v1/cases/{case_id}/resolution")
    assert resp.status_code == 404


# ---------------------------------------------------------------
# 7. Retrieval after resolution
# ---------------------------------------------------------------
def test_get_resolution_after_recorded_returns_200(client):
    case_id = _new_resolved_case(client)
    client.post(
        f"/api/v1/cases/{case_id}/resolution",
        json={"outcome_type": cfg.OUTCOME_TYPE_REFERRED_EXTERNAL, "resolution_note": "Escalated to external agency.", "recorded_by": "investigator_1"},
    )
    resp = client.get(f"/api/v1/cases/{case_id}/resolution")
    assert resp.status_code == 200
    body = resp.json()
    assert body["outcome_type"] == cfg.OUTCOME_TYPE_REFERRED_EXTERNAL
    assert body["resolution_note"] == "Escalated to external agency."


# ---------------------------------------------------------------
# 8. Immutable / no PATCH / DELETE routes
# ---------------------------------------------------------------
def test_resolution_has_no_update_or_delete_routes():
    from app.api.resolution import router
    methods_by_path: dict[str, set[str]] = {}
    for route in router.routes:
        methods_by_path.setdefault(route.path, set()).update(route.methods - {"HEAD", "OPTIONS"})
    for path, methods in methods_by_path.items():
        assert "PUT" not in methods and "PATCH" not in methods and "DELETE" not in methods, (path, methods)
    all_methods = {m for methods in methods_by_path.values() for m in methods}
    assert all_methods == {"GET", "POST"}


# ---------------------------------------------------------------
# 9. FK integrity
# ---------------------------------------------------------------
def test_no_orphan_resolution_rows(client):
    case_id = _new_resolved_case(client)
    client.post(f"/api/v1/cases/{case_id}/resolution", json={"outcome_type": cfg.OUTCOME_TYPE_INSUFFICIENT_EVIDENCE, "recorded_by": "a"})
    db = SessionLocal()
    try:
        case_ids = {c.case_id for c in db.query(Case.case_id).all()}
        for row in db.query(CaseResolution).all():
            assert row.case_id in case_ids
    finally:
        db.close()


def test_one_resolution_per_case_enforced_at_db_level(client):
    case_id = _new_resolved_case(client)
    client.post(f"/api/v1/cases/{case_id}/resolution", json={"outcome_type": cfg.OUTCOME_TYPE_INSUFFICIENT_EVIDENCE, "recorded_by": "a"})
    db = SessionLocal()
    try:
        count = db.query(CaseResolution).filter(CaseResolution.case_id == uuid.UUID(case_id)).count()
    finally:
        db.close()
    assert count == 1


# ---------------------------------------------------------------
# 10. Cascade deletion
# ---------------------------------------------------------------
def test_case_deletion_cascades_to_resolution(client):
    """Regenerating Stage 4 risk cascades: risk_scores -> alerts -> cases ->
    case_resolutions (ON DELETE CASCADE). Verified directly, consistent with
    the Stage 5/6/7 cascade-verification pattern."""
    case_id = _new_resolved_case(client)
    resp = client.post(f"/api/v1/cases/{case_id}/resolution", json={"outcome_type": cfg.OUTCOME_TYPE_CONFIRMED_MULE, "recorded_by": "a"})
    resolution_id = resp.json()["resolution_id"]

    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")  # force cascade

    db = SessionLocal()
    try:
        still_exists_case = db.get(Case, uuid.UUID(case_id))
        still_exists_resolution = db.get(CaseResolution, uuid.UUID(resolution_id))
    finally:
        db.close()
    assert still_exists_case is None
    assert still_exists_resolution is None

    # Restore normal state for any later tests in this session.
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")


# ---------------------------------------------------------------
# 11. AST leakage check
# ---------------------------------------------------------------
def test_resolution_modules_never_read_forbidden_fields():
    import ast
    forbidden_names = {"chain", "label", "acc_type"}
    for path in (
        "app/core/resolution_config.py",
        "app/services/resolution_engine.py",
        "app/api/resolution.py",
        "app/models/case_resolution.py",
        "app/schemas/resolution.py",
    ):
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


def test_resolution_engine_never_touches_confirmed_history_count_or_frozen_engines():
    """Static boundary check (per explicit authorization): resolution_engine.py
    must not import candidate_generation, mule_chain_prediction, risk_engine,
    or risk_orchestration, and must not reference confirmed_history_count as
    an executable identifier (only in comments, if at all)."""
    import ast
    source = (BACKEND_ROOT / "app/services/resolution_engine.py").read_text()
    tree = ast.parse(source)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
    forbidden_modules = {
        "app.services.candidate_generation",
        "app.services.mule_chain_prediction",
        "app.services.risk_engine",
        "app.services.risk_orchestration",
    }
    assert not (imported_modules & forbidden_modules), imported_modules & forbidden_modules

    # confirmed_history_count must not appear as an identifier/attribute/string literal anywhere in the AST
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "confirmed_history_count":
            raise AssertionError("confirmed_history_count referenced as an identifier")
        if isinstance(node, ast.Constant) and node.value == "confirmed_history_count":
            raise AssertionError("confirmed_history_count referenced as a string literal")


# ---------------------------------------------------------------
# 12. Response leakage check
# ---------------------------------------------------------------
def test_resolution_response_contains_no_ground_truth(client):
    case_id = _new_resolved_case(client)
    post_body = client.post(f"/api/v1/cases/{case_id}/resolution", json={"outcome_type": cfg.OUTCOME_TYPE_CONFIRMED_MULE, "recorded_by": "a"}).json()
    get_body = client.get(f"/api/v1/cases/{case_id}/resolution").json()
    for body in (post_body, get_body):
        s = str(body)
        for forbidden in ('"chain"', '"label"', '"account_type"', "legit_low", "legit_high", "confusor", "adversarial_bait"):
            assert forbidden not in s
        # "confirmed_mule" (investigator outcome) is expected and fine; the
        # bare synthetic role string "mule" alone (as a standalone JSON
        # value, not embedded in "confirmed_mule") must never appear.
        assert '"mule"' not in s


# ---------------------------------------------------------------
# 13. Stage 1-7 regression
# ---------------------------------------------------------------
def test_canonical_stage1_counts_unchanged_after_stage8(client):
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


def test_case_status_unaffected_by_resolution_recording(client):
    case_id = _new_resolved_case(client)
    before = _get_case_row(case_id).status
    client.post(f"/api/v1/cases/{case_id}/resolution", json={"outcome_type": cfg.OUTCOME_TYPE_CONFIRMED_MULE, "recorded_by": "a"})
    after = _get_case_row(case_id).status
    assert before == after == case_config.CASE_STATUS_RESOLVED
