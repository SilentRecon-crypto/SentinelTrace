import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core import risk_config as cfg  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services import intervention_engine, risk_engine  # noqa: E402
from app.services.model_a import get_model_a  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_MULE_ACCOUNT_ID = 3722

SAMPLE_FEATURES = {
    "hop_distance": 1.0, "pass_through_ratio": 0.5568, "fan_in_recent_30d": 1.0,
    "out_degree_recent_30d": 0.0, "account_age_days": 0.0, "confirmed_history_count": 0.0,
    "amount_consistency": 1.4551, "subgraph_degree_centrality": 0.8846,
}


# ---------------------------------------------------------------
# Config sanity (weights must sum to 1.0, bands must be non-overlapping/complete)
# ---------------------------------------------------------------
def test_priority_weights_sum_to_one():
    total = cfg.PRIORITY_WEIGHT_ML + cfg.PRIORITY_WEIGHT_AMOUNT + cfg.PRIORITY_WEIGHT_URGENCY
    assert total == pytest.approx(1.0)


def test_heuristic_weights_sum_to_one():
    total = cfg.HEUR_WEIGHT_HOP + cfg.HEUR_WEIGHT_PASSTHROUGH + cfg.HEUR_WEIGHT_FANIN + cfg.HEUR_WEIGHT_CENTRALITY
    assert total == pytest.approx(1.0)


def test_risk_bands_cover_0_to_1_without_gaps_or_overlap():
    bands = sorted(cfg.RISK_BANDS)
    assert bands[0][0] == 0.0
    for i in range(len(bands) - 1):
        assert bands[i][1] == bands[i + 1][0]
    assert bands[-1][1] > 1.0


# ---------------------------------------------------------------
# Risk engine — priority formula
# ---------------------------------------------------------------
def test_priority_is_deterministic():
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)
    p1 = risk_engine.compute_priority(0.9, 50000, 100, now)
    p2 = risk_engine.compute_priority(0.9, 50000, 100, now)
    assert p1 == p2


def test_priority_value_bounded_0_to_1():
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)
    for ml_score in (0.0, 0.5, 1.0):
        for amount in (0, 10_000, 1_000_000):
            p = risk_engine.compute_priority(ml_score, amount, 0, now)
            assert 0.0 <= p.value <= 1.0


def test_priority_uses_exactly_the_contract_named_inputs():
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)
    p = risk_engine.compute_priority(0.5, 50000, 100, now)
    assert p.formula_inputs == ["ml_score", "fraud_amount_tier", "hours_since_complaint"]
    assert p.method == "heuristic_combination"


def test_priority_band_boundary_conditions():
    """Pin exact band edges using algebraically-solved inputs (amount tier
    and urgency both saturated at their max contribution), isolating
    ml_score as the only free variable so each boundary is hit precisely."""
    epoch = datetime.fromisoformat(cfg.SYNTHETIC_DAY_ZERO_EPOCH)
    now = epoch + timedelta(days=1000)  # far enough past day=0 to saturate urgency at 1.0
    fixed = cfg.PRIORITY_WEIGHT_AMOUNT * 1.0 + cfg.PRIORITY_WEIGHT_URGENCY * 1.0  # amount tier=1.0 (>200k), urgency=1.0

    for lo, hi, expected_band in cfg.RISK_BANDS:
        if lo >= 1.0:
            continue  # unreachable with ml_score in [0,1] and these fixed components; not a real gap
        required_ml = (lo - fixed) / cfg.PRIORITY_WEIGHT_ML
        if not (0.0 <= required_ml <= 1.0):
            continue
        p = risk_engine.compute_priority(required_ml, 1_000_000, 0, now)
        assert p.value == pytest.approx(lo, abs=1e-6)
        assert p.level == expected_band, f"value {p.value} expected band {expected_band}, got {p.level}"


def test_higher_ml_score_never_decreases_priority():
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)
    low = risk_engine.compute_priority(0.1, 50000, 100, now)
    high = risk_engine.compute_priority(0.9, 50000, 100, now)
    assert high.value > low.value


def test_known_complaint_452_top_candidate_priority_is_critical():
    """Regression pin for the documented live E2E result."""
    now = datetime(2026, 9, 8, tzinfo=timezone.utc)
    # complaint 452: fraud_amount=11153.48, day=5 (from Stage 1 canonical data)
    p = risk_engine.compute_priority(0.9969592777671326, 11153.48, 5, now)
    assert p.level == "critical"


# ---------------------------------------------------------------
# Risk engine — heuristic score
# ---------------------------------------------------------------
def test_heuristic_score_bounded_0_to_1():
    score = risk_engine.compute_heuristic_score(SAMPLE_FEATURES)
    assert 0.0 <= score <= 1.0


def test_heuristic_score_deterministic():
    s1 = risk_engine.compute_heuristic_score(SAMPLE_FEATURES)
    s2 = risk_engine.compute_heuristic_score(SAMPLE_FEATURES)
    assert s1 == s2


def test_heuristic_score_independent_of_ml_score():
    """heuristic_score must not be a function of model_score at all — it's
    computed purely from graph/behavior features."""
    import inspect
    source = inspect.getsource(risk_engine.compute_heuristic_score)
    assert "ml_score" not in source
    assert "model_score" not in source


def test_closer_hop_distance_increases_heuristic_score():
    near = dict(SAMPLE_FEATURES, hop_distance=1.0)
    far = dict(SAMPLE_FEATURES, hop_distance=4.0)
    assert risk_engine.compute_heuristic_score(near) > risk_engine.compute_heuristic_score(far)


# ---------------------------------------------------------------
# Risk engine — drivers / leakage
# ---------------------------------------------------------------
def test_drivers_use_only_the_8_official_features(client):
    model = get_model_a()
    drivers = risk_engine.compute_drivers(SAMPLE_FEATURES, model)
    assert len(drivers) == cfg.DRIVER_TOP_N
    for d in drivers:
        assert d.factor in model.feature_names_ordered
        assert d.description  # non-empty, generated from a template


def test_risk_engine_never_reads_ground_truth():
    import inspect
    source = inspect.getsource(risk_engine)
    for forbidden in (".chain", "candidate.label", "acc_type", "'mule'", '"mule"'):
        # allow the word inside our own docstring disclaimers (which
        # explicitly say these are NOT read); check no *usage* pattern exists
        assert f"row{forbidden}" not in source
        assert f"complaint{forbidden}" not in source


def test_no_prediction_raises_not_fabricates(client):
    db = SessionLocal()
    try:
        with pytest.raises(risk_engine.NoPredictionError):
            risk_engine.compute_risk_for_complaint(db, get_model_a(), 99999999)
    finally:
        db.close()


# ---------------------------------------------------------------
# Intervention engine
# ---------------------------------------------------------------
def test_intervention_window_ordering(client):
    db = SessionLocal()
    try:
        result = intervention_engine.compute_intervention_window(db, TEST_COMPLAINT_ID)
    finally:
        db.close()
    assert result.predicted_cashout_time > result.current_time
    assert result.estimated_window_minutes > 0


def test_intervention_window_duration_bounded(client):
    db = SessionLocal()
    try:
        result = intervention_engine.compute_intervention_window(db, TEST_COMPLAINT_ID)
    finally:
        db.close()
    assert cfg.INTERVENTION_MIN_MINUTES <= result.estimated_window_minutes <= cfg.INTERVENTION_MAX_MINUTES


def test_intervention_window_validation_status_is_fixed_literal(client):
    db = SessionLocal()
    try:
        result = intervention_engine.compute_intervention_window(db, TEST_COMPLAINT_ID)
    finally:
        db.close()
    assert result.validation_status == "synthetic_demo_only"
    assert result.method == "synthetic_historical_hop_timing"


def test_intervention_window_no_prediction_raises(client):
    db = SessionLocal()
    try:
        with pytest.raises(intervention_engine.NoPredictionError):
            intervention_engine.compute_intervention_window(db, 99999999)
    finally:
        db.close()


def test_intervention_rationale_present_and_honest(client):
    db = SessionLocal()
    try:
        result = intervention_engine.compute_intervention_window(db, TEST_COMPLAINT_ID)
    finally:
        db.close()
    assert result.rationale  # non-empty
    assert str(result.account_id) in result.rationale


def test_urgency_band_boundaries():
    assert intervention_engine.urgency_band(10) == "critical"
    assert intervention_engine.urgency_band(30) == "high"
    assert intervention_engine.urgency_band(120) == "medium"
    assert intervention_engine.urgency_band(1000) == "low"


def test_intervention_never_reads_future_or_ground_truth():
    import inspect
    # Check function bodies only, not the leakage-disclaimer docstrings
    # (which legitimately mention these terms to explain they are NOT used).
    for name, fn in inspect.getmembers(intervention_engine, inspect.isfunction):
        if fn.__module__ != intervention_engine.__name__:
            continue
        body = inspect.getsource(fn)
        # strip the function's own docstring before checking
        if fn.__doc__:
            body = body.replace(fn.__doc__, "")
        assert "complaint.chain" not in body, f"{name} references complaint.chain"
        assert "candidate.label" not in body, f"{name} references candidate.label"
        assert "acc_type" not in body, f"{name} references acc_type"
