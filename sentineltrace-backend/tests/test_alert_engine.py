import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core import alert_config as cfg  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services import alert_engine  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_MULE_ACCOUNT_ID = 3722


def _ensure_risk_exists(client):
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    client.post(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/risk")


# ---------------------------------------------------------------
# Config sanity
# ---------------------------------------------------------------
def test_alert_priority_weights_sum_to_one():
    total = cfg.ALERT_PRIORITY_WEIGHT_RISK + cfg.ALERT_PRIORITY_WEIGHT_URGENCY
    assert total == pytest.approx(1.0)


def test_alert_triggering_levels_are_subset_of_risk_bands():
    from app.core import risk_config as risk_cfg
    valid_levels = {band for _, _, band in risk_cfg.RISK_BANDS}
    assert set(cfg.ALERT_TRIGGERING_PRIORITY_LEVELS).issubset(valid_levels)


def test_alert_status_default_is_valid():
    assert cfg.ALERT_STATUS_DEFAULT in cfg.ALERT_VALID_STATUSES


# ---------------------------------------------------------------
# Engine — trigger / non-trigger conditions
# ---------------------------------------------------------------
def test_no_risk_score_raises(client):
    db = SessionLocal()
    try:
        from app.models.alert import Alert
        from app.models.complaint import Complaint
        from app.models.risk import RiskScore
        alerted_or_risked = {r.complaint_id for r in db.query(RiskScore.complaint_id).all()}
        candidate = db.query(Complaint).filter(~Complaint.complaint_id.in_(alerted_or_risked)).first()
    finally:
        db.close()
    if candidate is None:
        return  # every complaint already has a risk score this session; nothing to assert
    db = SessionLocal()
    try:
        with pytest.raises(alert_engine.NoRiskScoreError):
            alert_engine.compute_alerts_for_complaint(db, candidate.complaint_id)
    finally:
        db.close()


def test_only_high_and_critical_priority_generate_alerts(client):
    _ensure_risk_exists(client)
    db = SessionLocal()
    try:
        results = alert_engine.compute_alerts_for_complaint(db, TEST_COMPLAINT_ID)
    finally:
        db.close()
    for r in results:
        assert r.severity in cfg.ALERT_TRIGGERING_PRIORITY_LEVELS


def test_top_ranked_critical_intervention_gets_upgraded_type(client):
    """Complaint 452's canonical top account (3722) has priority level
    'critical' (Stage 4 canonical) and its intervention urgency band
    determines whether it gets the upgraded alert_type."""
    _ensure_risk_exists(client)
    db = SessionLocal()
    try:
        results = alert_engine.compute_alerts_for_complaint(db, TEST_COMPLAINT_ID)
    finally:
        db.close()
    top = next((r for r in results if r.account_id == KNOWN_MULE_ACCOUNT_ID), None)
    assert top is not None
    assert top.alert_type in (cfg.ALERT_TYPE_MULE_CHAIN, cfg.ALERT_TYPE_INTERVENTION_URGENCY)
    assert top.rank == 1


# ---------------------------------------------------------------
# Engine — determinism
# ---------------------------------------------------------------
def test_alert_generation_is_deterministic(client):
    _ensure_risk_exists(client)
    db = SessionLocal()
    try:
        first = alert_engine.compute_alerts_for_complaint(db, TEST_COMPLAINT_ID)
        second = alert_engine.compute_alerts_for_complaint(db, TEST_COMPLAINT_ID)
    finally:
        db.close()
    first_by_account = {r.account_id: (r.alert_type, r.severity, r.priority_score, r.title, r.explanation) for r in first}
    second_by_account = {r.account_id: (r.alert_type, r.severity, r.priority_score, r.title, r.explanation) for r in second}
    assert first_by_account == second_by_account


def test_priority_score_is_not_called_probability():
    """priority_score must never be labeled a probability anywhere in code
    comments/templates that ship into user-facing text."""
    for template in (cfg.ALERT_TITLE_TEMPLATE_MULE_CHAIN, cfg.ALERT_TITLE_TEMPLATE_INTERVENTION):
        assert "probability" not in template.lower()


# ---------------------------------------------------------------
# Leakage protection
# ---------------------------------------------------------------
def test_alert_engine_never_reads_forbidden_fields(client):
    """AST-based check: alert_engine.py must never contain executable
    attribute/subscript/keyword access to forbidden ground-truth names.

    NOTE (Stage 5 static audit fix): this test previously did a naive
    substring search for '.chain', '.label', '.acc_type' etc. against the
    raw source text. That is unsound — it also matches PROSE in the
    module's own docstring (e.g. "...never complaints.chain, never
    accounts.acc_type, never candidate.label...", which documents what the
    module does NOT do) and would fail the file for talking about the very
    leakage protection it implements. Parsing the file into an AST and only
    inspecting real Attribute/Subscript/keyword nodes correctly ignores
    docstrings/comments while still catching genuine executable access.
    """
    import ast

    source = (BACKEND_ROOT / "app" / "services" / "alert_engine.py").read_text()
    tree = ast.parse(source)
    forbidden_names = {"chain", "label", "acc_type"}

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in forbidden_names:
            violations.append(f"attribute access .{node.attr} at line {node.lineno}")
        elif isinstance(node, ast.Subscript):
            sl = node.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str) and sl.value in forbidden_names:
                violations.append(f"subscript access [{sl.value!r}] at line {node.lineno}")
        elif isinstance(node, ast.keyword) and node.arg in forbidden_names:
            violations.append(f"keyword argument {node.arg}= at line {node.lineno}")

    assert not violations, f"Forbidden ground-truth access found: {violations}"


def test_generated_alert_explanations_contain_no_ground_truth(client):
    _ensure_risk_exists(client)
    db = SessionLocal()
    try:
        results = alert_engine.compute_alerts_for_complaint(db, TEST_COMPLAINT_ID)
    finally:
        db.close()
    for r in results:
        text = r.title + " " + r.explanation
        for forbidden in ("legit_low", "legit_high", "confusor", "adversarial_bait"):
            assert forbidden not in text
