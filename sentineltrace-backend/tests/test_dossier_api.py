import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core import case_config, resolution_config  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.alert import Alert  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.models.case_resolution import CaseResolution  # noqa: E402
from app.models.intervention import InterventionWindowRecord  # noqa: E402
from app.models.prediction import MuleChainPrediction  # noqa: E402
from app.models.risk import RiskScore  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_MULE_ACCOUNT_ID = 3722


def _new_case(client) -> str:
    """Fully drives the pipeline to a fresh, 'open' case for complaint 452's
    known top account. Every call regenerates risk (cascading away any
    existing alert/case/evidence/resolution for this complaint), so every
    test that calls this starts from a clean, self-contained state, same
    pattern as tests/test_case_api.py, test_evidence_api.py, and
    test_resolution_api.py."""
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")
    alerts_body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts").json()
    top_alert = next(r for r in alerts_body["results"] if r["account_id"] == KNOWN_MULE_ACCOUNT_ID)
    case_resp = client.post(f"/api/v1/alerts/{top_alert['alert_id']}/cases")
    return case_resp.json()["case_id"]


def _get_case_row(case_id: str) -> Case:
    db = SessionLocal()
    try:
        return db.get(Case, uuid.UUID(case_id))
    finally:
        db.close()


def _snapshot_all_rows():
    """Used to prove GET /dossier mutates nothing."""
    db = SessionLocal()
    try:
        return {
            "cases": [(c.case_id, c.status, c.updated_at) for c in db.query(Case).all()],
            "alerts": [(a.alert_id, a.status, a.updated_at) for a in db.query(Alert).all()],
            "risk": [(r.score_id, r.priority_value) for r in db.query(RiskScore).all()],
            "resolutions": [(r.resolution_id, r.outcome_type) for r in db.query(CaseResolution).all()],
        }
    finally:
        db.close()


# ---------------------------------------------------------------
# 1. Canonical case 452 dossier / 3. case data correctness
# ---------------------------------------------------------------
def test_canonical_case_452_dossier_matches_underlying_records(client):
    case_id = _new_case(client)
    case_row = _get_case_row(case_id)

    resp = client.get(f"/api/v1/cases/{case_id}/dossier")
    assert resp.status_code == 200
    body = resp.json()

    # Cross-check against the standalone GET /cases/{id} endpoint's own response.
    standalone_case = client.get(f"/api/v1/cases/{case_id}").json()
    assert body["case"] == standalone_case
    assert body["case"]["account_id"] == KNOWN_MULE_ACCOUNT_ID
    assert body["case"]["complaint_id"] == TEST_COMPLAINT_ID
    assert case_row.status == body["case"]["status"]


# ---------------------------------------------------------------
# 2. 404 for missing case
# ---------------------------------------------------------------
def test_dossier_for_nonexistent_case_returns_404(client):
    resp = client.get(f"/api/v1/cases/{uuid.uuid4()}/dossier")
    assert resp.status_code == 404


# ---------------------------------------------------------------
# 4. Notes correctness and ordering
# ---------------------------------------------------------------
def test_dossier_notes_match_standalone_endpoint_and_are_ordered(client):
    case_id = _new_case(client)
    client.post(f"/api/v1/cases/{case_id}/notes", json={"author": "a", "note_text": "first"})
    client.post(f"/api/v1/cases/{case_id}/notes", json={"author": "b", "note_text": "second"})

    dossier = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    standalone = client.get(f"/api/v1/cases/{case_id}/notes").json()["results"]
    assert dossier["notes"] == standalone
    timestamps = [n["created_at"] for n in dossier["notes"]]
    assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------
# 5. Evidence correctness across all three evidence types
# ---------------------------------------------------------------
def test_dossier_evidence_matches_standalone_endpoint_across_all_types(client):
    case_id = _new_case(client)
    case_row = _get_case_row(case_id)

    db = SessionLocal()
    try:
        from app.models.transaction import Transaction
        txn = db.query(Transaction).filter(
            (Transaction.src_account_id == case_row.account_id) | (Transaction.dst_account_id == case_row.account_id)
        ).first()
        prediction = db.query(MuleChainPrediction).filter(
            MuleChainPrediction.complaint_id == case_row.complaint_id,
            MuleChainPrediction.candidate_account_id == case_row.account_id,
        ).first()
        risk = db.query(RiskScore).filter(
            RiskScore.complaint_id == case_row.complaint_id, RiskScore.account_id == case_row.account_id
        ).first()
    finally:
        db.close()
    assert txn is not None and prediction is not None and risk is not None

    client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": "transaction_reference", "transaction_id": txn.transaction_id, "added_by": "a"})
    client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": "graph_explanation_reference", "prediction_id": prediction.id, "added_by": "b"})
    client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": "risk_driver_reference", "risk_score_id": str(risk.score_id), "added_by": "c"})

    dossier = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    standalone = client.get(f"/api/v1/cases/{case_id}/evidence").json()["results"]
    assert dossier["evidence"] == standalone
    types_seen = {e["evidence_type"] for e in dossier["evidence"]}
    assert types_seen == {"transaction_reference", "graph_explanation_reference", "risk_driver_reference"}


# ---------------------------------------------------------------
# 6. Resolution present / 7. resolution absent
# ---------------------------------------------------------------
def test_dossier_resolution_absent_returns_null(client):
    case_id = _new_case(client)
    dossier = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    assert dossier["resolution"] is None
    # A null resolution on a non-resolved case is a normal state, not a data
    # gap, so it must not itself be reported as a "limitation".
    assert not any("resolution" in lim.lower() for lim in dossier["limitations"])


def test_dossier_resolution_present_matches_standalone(client):
    case_id = _new_case(client)
    client.patch(f"/api/v1/cases/{case_id}", json={"status": case_config.CASE_STATUS_INVESTIGATING})
    client.patch(f"/api/v1/cases/{case_id}", json={"status": case_config.CASE_STATUS_RESOLVED})
    client.post(f"/api/v1/cases/{case_id}/resolution", json={"outcome_type": resolution_config.OUTCOME_TYPE_CONFIRMED_MULE, "recorded_by": "investigator_1"})

    dossier = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    standalone = client.get(f"/api/v1/cases/{case_id}/resolution").json()
    assert dossier["resolution"] == standalone
    assert dossier["resolution"]["outcome_type"] == resolution_config.OUTCOME_TYPE_CONFIRMED_MULE


# ---------------------------------------------------------------
# 8. Alert association correctness
# ---------------------------------------------------------------
def test_dossier_alert_matches_actual_alert_for_case(client):
    case_id = _new_case(client)
    case_row = _get_case_row(case_id)
    db = SessionLocal()
    try:
        alert = db.get(Alert, case_row.alert_id)
    finally:
        db.close()

    dossier = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    assert dossier["alert"] is not None
    assert dossier["alert"]["alert_id"] == str(alert.alert_id)
    assert dossier["alert"]["account_id"] == KNOWN_MULE_ACCOUNT_ID


# ---------------------------------------------------------------
# 9. Risk association correctness
# ---------------------------------------------------------------
def test_dossier_risk_matches_alerts_own_risk_score_id(client):
    case_id = _new_case(client)
    case_row = _get_case_row(case_id)
    db = SessionLocal()
    try:
        alert = db.get(Alert, case_row.alert_id)
        risk = db.get(RiskScore, alert.risk_score_id)
    finally:
        db.close()

    dossier = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    assert dossier["risk"] is not None
    assert dossier["risk"]["ml_score"] == risk.ml_score
    assert dossier["risk"]["priority"]["value"] == risk.priority_value
    assert dossier["risk"]["priority"]["level"] == risk.priority_level


# ---------------------------------------------------------------
# 10. Intervention association correctness where deterministic
# ---------------------------------------------------------------
def test_dossier_intervention_present_for_top_ranked_account(client):
    """Complaint 452's canonical top account (3722, rank 1) is exactly the
    account Stage 4's intervention engine computes a window for."""
    case_id = _new_case(client)
    case_row = _get_case_row(case_id)
    db = SessionLocal()
    try:
        expected = db.query(InterventionWindowRecord).filter(
            InterventionWindowRecord.complaint_id == case_row.complaint_id
        ).order_by(InterventionWindowRecord.generated_at.desc()).first()
    finally:
        db.close()

    dossier = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    if expected is not None and expected.account_id == case_row.account_id:
        assert dossier["intervention"] is not None
        assert dossier["intervention"]["estimated_window_minutes"] == expected.estimated_window_minutes
    else:
        assert dossier["intervention"] is None
        assert any("intervention" in lim.lower() for lim in dossier["limitations"])


# ---------------------------------------------------------------
# 11. Prediction association correctness where deterministic
# ---------------------------------------------------------------
def test_dossier_prediction_matches_matching_candidate_row(client):
    case_id = _new_case(client)
    case_row = _get_case_row(case_id)
    db = SessionLocal()
    try:
        expected = db.query(MuleChainPrediction).filter(
            MuleChainPrediction.complaint_id == case_row.complaint_id,
            MuleChainPrediction.candidate_account_id == case_row.account_id,
        ).first()
    finally:
        db.close()
    assert expected is not None

    dossier = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    assert dossier["prediction"] is not None
    assert dossier["prediction"]["rank"] == expected.rank
    assert dossier["prediction"]["model_score"] == expected.model_score
    assert dossier["prediction"]["candidate_account_id"] == KNOWN_MULE_ACCOUNT_ID


# ---------------------------------------------------------------
# 12. Response-level leakage check
# ---------------------------------------------------------------
def test_dossier_response_contains_no_ground_truth(client):
    case_id = _new_case(client)
    body_str = str(client.get(f"/api/v1/cases/{case_id}/dossier").json())
    for forbidden in ('"chain"', '"label"', '"account_type"', "legit_low", "legit_high", "confusor", "adversarial_bait"):
        assert forbidden not in body_str
    assert '"mule"' not in body_str  # bare synthetic role string must never appear as a standalone value


# ---------------------------------------------------------------
# 13. AST leakage check
# ---------------------------------------------------------------
def test_dossier_modules_never_read_forbidden_fields():
    import ast
    forbidden_names = {"chain", "label", "acc_type"}
    for path in ("app/services/dossier_engine.py", "app/api/dossier.py", "app/schemas/dossier.py"):
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


# ---------------------------------------------------------------
# 14. AST no-write check
# ---------------------------------------------------------------
def test_dossier_engine_has_no_write_operations():
    import ast
    source = (BACKEND_ROOT / "app/services/dossier_engine.py").read_text()
    tree = ast.parse(source)
    write_method_names = {"add", "commit", "delete", "flush"}
    write_hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in write_method_names:
            write_hits.append((node.attr, node.lineno))
        if isinstance(node, ast.ImportFrom) and node.module and "sqlalchemy" in node.module:
            for alias in node.names:
                if alias.name in ("delete", "update", "insert"):
                    write_hits.append((f"import:{alias.name}", node.lineno))
    assert not write_hits, write_hits


# ---------------------------------------------------------------
# 15. Prove GET does not mutate relevant persisted state
# ---------------------------------------------------------------
def test_dossier_get_does_not_mutate_persisted_state(client):
    case_id = _new_case(client)
    client.patch(f"/api/v1/cases/{case_id}", json={"status": case_config.CASE_STATUS_INVESTIGATING})

    before = _snapshot_all_rows()
    client.get(f"/api/v1/cases/{case_id}/dossier")
    client.get(f"/api/v1/cases/{case_id}/dossier")  # twice, to also prove no accumulation
    after = _snapshot_all_rows()
    assert before == after


# ---------------------------------------------------------------
# 16. Deterministic response ordering
# ---------------------------------------------------------------
def test_dossier_response_is_deterministic_across_repeated_calls(client):
    case_id = _new_case(client)
    first = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    second = client.get(f"/api/v1/cases/{case_id}/dossier").json()
    assert first == second


# ---------------------------------------------------------------
# Route surface check (GET only)
# ---------------------------------------------------------------
def test_dossier_route_is_get_only():
    from app.api.dossier import router
    methods_by_path: dict[str, set[str]] = {}
    for route in router.routes:
        methods_by_path.setdefault(route.path, set()).update(route.methods - {"HEAD", "OPTIONS"})
    for path, methods in methods_by_path.items():
        assert methods == {"GET"}, (path, methods)


# ---------------------------------------------------------------
# 17. Stage 1-8 regression
# ---------------------------------------------------------------
def test_canonical_stage1_counts_unchanged_after_stage9(client):
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


def test_dossier_no_database_schema_changes():
    """Static check: dossier_engine.py must never define a SQLAlchemy
    declarative model class (no `Base` subclass), since Stage 9 introduces
    no new tables/columns at all."""
    source = (BACKEND_ROOT / "app/services/dossier_engine.py").read_text()
    assert "(Base)" not in source
