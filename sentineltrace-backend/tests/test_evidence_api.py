import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core import evidence_config as cfg  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.models.evidence import CaseEvidenceGraphExplanation, CaseEvidenceRiskDriver, CaseEvidenceTransaction  # noqa: E402
from app.models.prediction import MuleChainPrediction  # noqa: E402
from app.models.risk import RiskScore  # noqa: E402
from app.models.transaction import Transaction  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_MULE_ACCOUNT_ID = 3722


def _ensure_case_exists(client) -> str:
    """Fully drives the pipeline to a fresh case for complaint 452's known
    top account, returning its case_id. Every call regenerates risk (which
    cascades to delete any existing alert/case for this complaint — see
    Stage 6's README note), so every test that calls this starts from a
    clean, self-contained state, same pattern as tests/test_case_api.py."""
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


def _find_relevant_transaction_id(case_row: Case) -> int | None:
    db = SessionLocal()
    try:
        txn = (
            db.query(Transaction)
            .filter((Transaction.src_account_id == case_row.account_id) | (Transaction.dst_account_id == case_row.account_id))
            .first()
        )
        return txn.transaction_id if txn else None
    finally:
        db.close()


def _find_matching_prediction_id(case_row: Case) -> int | None:
    db = SessionLocal()
    try:
        p = (
            db.query(MuleChainPrediction)
            .filter(
                MuleChainPrediction.complaint_id == case_row.complaint_id,
                MuleChainPrediction.candidate_account_id == case_row.account_id,
            )
            .first()
        )
        return p.id if p else None
    finally:
        db.close()


def _find_matching_risk_score(case_row: Case) -> RiskScore | None:
    db = SessionLocal()
    try:
        return (
            db.query(RiskScore)
            .filter(RiskScore.complaint_id == case_row.complaint_id, RiskScore.account_id == case_row.account_id)
            .first()
        )
    finally:
        db.close()


# ---------------------------------------------------------------
# Config sanity
# ---------------------------------------------------------------
def test_evidence_types_are_exactly_the_authorized_closed_set():
    assert set(cfg.EVIDENCE_VALID_TYPES) == {
        "transaction_reference",
        "graph_explanation_reference",
        "risk_driver_reference",
    }


# ---------------------------------------------------------------
# 1. Valid transaction evidence
# ---------------------------------------------------------------
def test_valid_transaction_evidence(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    txn_id = _find_relevant_transaction_id(case_row)
    assert txn_id is not None, "expected at least one transaction involving the canonical mule account"

    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "transaction_id": txn_id, "added_by": "investigator_1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["evidence_type"] == cfg.EVIDENCE_TYPE_TRANSACTION
    assert body["transaction_id"] == txn_id
    assert body["prediction_id"] is None
    assert body["risk_score_id"] is None


# ---------------------------------------------------------------
# 2. Invalid transaction reference
# ---------------------------------------------------------------
def test_transaction_evidence_nonexistent_transaction_returns_404(client):
    case_id = _ensure_case_exists(client)
    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "transaction_id": 999999999, "added_by": "investigator_1"},
    )
    assert resp.status_code == 404


def test_transaction_evidence_unrelated_transaction_returns_422(client):
    """A transaction that EXISTS but doesn't involve this case's account
    must be rejected as an invalid reference target, not silently accepted."""
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    db = SessionLocal()
    try:
        unrelated = (
            db.query(Transaction)
            .filter(Transaction.src_account_id != case_row.account_id, Transaction.dst_account_id != case_row.account_id)
            .first()
        )
    finally:
        db.close()
    assert unrelated is not None
    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "transaction_id": unrelated.transaction_id, "added_by": "investigator_1"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------
# 3. Valid graph/explanation reference
# ---------------------------------------------------------------
def test_valid_graph_explanation_evidence(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    prediction_id = _find_matching_prediction_id(case_row)
    assert prediction_id is not None

    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION, "prediction_id": prediction_id, "added_by": "investigator_1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["evidence_type"] == cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION
    assert body["prediction_id"] == prediction_id


def test_graph_explanation_evidence_wrong_account_returns_422(client):
    """A prediction row that exists but belongs to a different candidate
    account within the same complaint must be rejected."""
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    db = SessionLocal()
    try:
        other = (
            db.query(MuleChainPrediction)
            .filter(
                MuleChainPrediction.complaint_id == case_row.complaint_id,
                MuleChainPrediction.candidate_account_id != case_row.account_id,
            )
            .first()
        )
    finally:
        db.close()
    if other is None:
        return  # complaint 452 only ever had one candidate this run; nothing to assert
    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION, "prediction_id": other.id, "added_by": "investigator_1"},
    )
    assert resp.status_code == 422


def test_graph_explanation_evidence_nonexistent_prediction_returns_404(client):
    case_id = _ensure_case_exists(client)
    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION, "prediction_id": 999999999, "added_by": "investigator_1"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------
# 4. Valid risk-driver reference
# ---------------------------------------------------------------
def test_valid_risk_driver_evidence_whole_score(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    risk = _find_matching_risk_score(case_row)
    assert risk is not None

    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_RISK_DRIVER, "risk_score_id": str(risk.score_id), "added_by": "investigator_1"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["evidence_type"] == cfg.EVIDENCE_TYPE_RISK_DRIVER
    assert body["risk_score_id"] == str(risk.score_id)
    assert body["driver_index"] is None


def test_valid_risk_driver_evidence_specific_index(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    risk = _find_matching_risk_score(case_row)
    assert risk is not None and len(risk.drivers) >= 1

    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_RISK_DRIVER, "risk_score_id": str(risk.score_id), "driver_index": 0, "added_by": "investigator_1"},
    )
    assert resp.status_code == 201
    assert resp.json()["driver_index"] == 0


def test_risk_driver_evidence_out_of_range_index_returns_422(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    risk = _find_matching_risk_score(case_row)
    assert risk is not None

    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_RISK_DRIVER, "risk_score_id": str(risk.score_id), "driver_index": len(risk.drivers) + 50, "added_by": "investigator_1"},
    )
    assert resp.status_code == 422


def test_risk_driver_evidence_nonexistent_score_returns_404(client):
    case_id = _ensure_case_exists(client)
    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_RISK_DRIVER, "risk_score_id": str(uuid.uuid4()), "added_by": "investigator_1"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------
# 5. Invalid evidence type
# ---------------------------------------------------------------
def test_invalid_evidence_type_returns_422(client):
    case_id = _ensure_case_exists(client)
    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": "not_a_real_type", "transaction_id": 1, "added_by": "investigator_1"},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------
# 6. Missing case
# ---------------------------------------------------------------
def test_evidence_for_nonexistent_case_returns_404(client):
    resp = client.post(
        f"/api/v1/cases/{uuid.uuid4()}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "transaction_id": 1, "added_by": "investigator_1"},
    )
    assert resp.status_code == 404


def test_get_evidence_for_nonexistent_case_returns_404(client):
    resp = client.get(f"/api/v1/cases/{uuid.uuid4()}/evidence")
    assert resp.status_code == 404


# ---------------------------------------------------------------
# Malformed request (wrong fields for the given type)
# ---------------------------------------------------------------
def test_malformed_request_extra_fields_for_type_returns_422(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    txn_id = _find_relevant_transaction_id(case_row)
    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={
            "evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION,
            "transaction_id": txn_id,
            "risk_score_id": str(uuid.uuid4()),  # not allowed alongside transaction_reference
            "added_by": "investigator_1",
        },
    )
    assert resp.status_code == 422


def test_malformed_request_missing_required_field_returns_422(client):
    case_id = _ensure_case_exists(client)
    resp = client.post(
        f"/api/v1/cases/{case_id}/evidence",
        json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "added_by": "investigator_1"},  # no transaction_id
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------
# 7. Append-only behavior
# ---------------------------------------------------------------
def test_evidence_has_no_update_or_delete_routes():
    from app.api.evidence import router
    methods_by_path: dict[str, set[str]] = {}
    for route in router.routes:
        methods_by_path.setdefault(route.path, set()).update(route.methods - {"HEAD", "OPTIONS"})
    for path, methods in methods_by_path.items():
        assert "PUT" not in methods and "PATCH" not in methods and "DELETE" not in methods, (path, methods)


# ---------------------------------------------------------------
# 8. Evidence retrieval / 9. ordering
# ---------------------------------------------------------------
def test_retrieve_evidence_after_attaching_multiple_types(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    txn_id = _find_relevant_transaction_id(case_row)
    prediction_id = _find_matching_prediction_id(case_row)
    risk = _find_matching_risk_score(case_row)

    client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "transaction_id": txn_id, "added_by": "a"})
    client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION, "prediction_id": prediction_id, "added_by": "b"})
    client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": cfg.EVIDENCE_TYPE_RISK_DRIVER, "risk_score_id": str(risk.score_id), "added_by": "c"})

    resp = client.get(f"/api/v1/cases/{case_id}/evidence")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    types_seen = {r["evidence_type"] for r in body["results"]}
    assert types_seen == {cfg.EVIDENCE_TYPE_TRANSACTION, cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION, cfg.EVIDENCE_TYPE_RISK_DRIVER}

    timestamps = [r["created_at"] for r in body["results"]]
    assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------
# 10. DB foreign-key integrity
# ---------------------------------------------------------------
def test_no_orphan_evidence_rows(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    txn_id = _find_relevant_transaction_id(case_row)
    client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "transaction_id": txn_id, "added_by": "a"})

    db = SessionLocal()
    try:
        case_ids = {c.case_id for c in db.query(Case.case_id).all()}
        txn_ids = {t.transaction_id for t in db.query(Transaction.transaction_id).all()}
        for row in db.query(CaseEvidenceTransaction).all():
            assert row.case_id in case_ids
            assert row.transaction_id in txn_ids
    finally:
        db.close()


# ---------------------------------------------------------------
# 11. Cascade deletion
# ---------------------------------------------------------------
def test_case_deletion_cascades_to_evidence(client):
    """Regenerating Stage 4 risk cascades: risk_scores -> alerts -> cases ->
    case_evidence_* (all ON DELETE CASCADE). Verified directly, not assumed,
    consistent with the Stage 5/6 cascade-verification pattern."""
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    txn_id = _find_relevant_transaction_id(case_row)
    resp = client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "transaction_id": txn_id, "added_by": "a"})
    evidence_id = resp.json()["evidence_id"]

    # Force another risk regeneration -> cascades all the way down.
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")

    db = SessionLocal()
    try:
        still_exists_case = db.get(Case, uuid.UUID(case_id))
        still_exists_evidence = db.get(CaseEvidenceTransaction, uuid.UUID(evidence_id))
    finally:
        db.close()
    assert still_exists_case is None
    assert still_exists_evidence is None

    # Restore normal state for any later tests in this session.
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/alerts/generate")


# ---------------------------------------------------------------
# 12. Leakage protection (AST-based, per Stage 5/6 audit pattern)
# ---------------------------------------------------------------
def test_evidence_modules_never_read_forbidden_fields():
    import ast
    forbidden_names = {"chain", "label", "acc_type"}
    for path in ("app/services/evidence_engine.py", "app/api/evidence.py", "app/models/evidence.py", "app/schemas/evidence.py"):
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


def test_evidence_response_contains_no_ground_truth(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    txn_id = _find_relevant_transaction_id(case_row)
    post_body = client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "transaction_id": txn_id, "added_by": "a"}).json()
    get_body = client.get(f"/api/v1/cases/{case_id}/evidence").json()
    for body in (post_body, get_body):
        s = str(body)
        for forbidden in ('"chain"', '"label"', '"account_type"', "legit_low", "legit_high", "confusor", "adversarial_bait", 'mule"'):
            assert forbidden not in s


# ---------------------------------------------------------------
# 13. Stage 1-6 regression
# ---------------------------------------------------------------
def test_canonical_stage1_counts_unchanged_after_stage7(client):
    db = SessionLocal()
    try:
        from app.models.account import Account
        from app.models.complaint import Complaint
        assert db.query(Account).count() == 4025
        assert db.query(Transaction).count() == 38830
        assert db.query(Complaint).count() == 500
    finally:
        db.close()


def test_case_unaffected_by_evidence_attachment(client):
    case_id = _ensure_case_exists(client)
    case_row = _get_case_row(case_id)
    txn_id = _find_relevant_transaction_id(case_row)
    before = SessionLocal()
    try:
        before_status = before.get(Case, uuid.UUID(case_id)).status
    finally:
        before.close()

    client.post(f"/api/v1/cases/{case_id}/evidence", json={"evidence_type": cfg.EVIDENCE_TYPE_TRANSACTION, "transaction_id": txn_id, "added_by": "a"})

    after = SessionLocal()
    try:
        after_status = after.get(Case, uuid.UUID(case_id)).status
    finally:
        after.close()
    assert before_status == after_status
