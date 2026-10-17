"""
Risk engine (Stage 4).

Implements SentinelTrace_Technical_Contract.md §10 (Risk Engine Contract).
Consumes the EXISTING, already-persisted Model A prediction output
(app.models.prediction.MuleChainPrediction, from Stage 3A/3B, unchanged)
and derives three separate, clearly-labeled numbers per Contract §10:

    ml_score          <- Model A's own output, copied verbatim, never touched
    heuristic_score    <- pure graph-topology "flow-decay" formula, independent of ml_score
    priority           <- {level, value, method, formula_inputs} — the operational
                          prioritization signal, a weighted combination of
                          ml_score + fraud_amount_tier + hours_since_complaint
                          (exactly Contract §10's named formula_inputs)

`priority.method` is always the fixed literal "heuristic_combination" per
Contract §10 — there is no labeled outcome data to train a priority model
on, and the Contract forbids presenting it as anything else.

GROUND-TRUTH ISOLATION: this module reads only persisted MuleChainPrediction
rows (already leakage-safe, Stage 3A/3B) and Complaint.fraud_amount/day
(legitimate intake fields). It never reads complaints.chain, never reads
accounts.acc_type, and never reads candidate.label (which doesn't even
reach persistence — see Stage 3A).
"""
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core import risk_config as cfg
from app.models.complaint import Complaint
from app.models.prediction import MuleChainPrediction
from app.services.model_a import ModelARegistry

RESEARCH_DIR = Path(__file__).resolve().parent.parent.parent / "research_model_a"
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))


class NoPredictionError(RuntimeError):
    """Raised when risk is requested for a complaint with no persisted Model A prediction."""


@dataclass
class Driver:
    factor: str
    contribution: float  # the candidate's raw feature value (not a SHAP contribution)
    description: str


@dataclass
class Priority:
    level: str
    value: float
    method: str
    formula_inputs: list[str]


@dataclass
class RiskResult:
    complaint_id: int
    account_id: int
    ml_score: float
    heuristic_score: float
    priority: Priority
    drivers: list[Driver]
    generated_at: datetime


# ---------------------------------------------------------------
# Permutation importance — computed ONCE from the existing frozen model
# against Stage 1's own evaluation-only held-out split (candidates.csv +
# training_metadata.json's recorded split_day). This is a read-only,
# post-hoc analysis of an already-trained estimator: it does NOT retrain,
# refit, or modify model_a_v1.pkl in any way. Cached in-process memory only
# — deliberately NOT written back into artifacts/model_a/feature_metadata.json,
# so that Stage 1 artifact stays byte-identical on disk per Stage 4 scope rules.
# ---------------------------------------------------------------
@lru_cache(maxsize=1)
def _permutation_importance_ranking(feature_names: tuple[str, ...]) -> list[str]:
    from sklearn.inspection import permutation_importance

    from app.services.model_a import get_model_a

    registry = get_model_a()
    training_meta = registry.training_metadata
    split_day = training_meta["train_test_split"]["split_day"]

    candidates_path = BACKEND_ROOT / "data" / "model_a" / "candidates.csv"
    candidates = pd.read_csv(candidates_path)
    complaints_path = BACKEND_ROOT / "data" / "model_a" / "complaints.csv"
    complaints = pd.read_csv(complaints_path)[["complaint_id", "day"]]
    merged = candidates.merge(complaints, on="complaint_id", suffixes=("", "_complaint"))
    test = merged[merged["day_complaint"] >= split_day] if "day_complaint" in merged.columns else merged[merged["day"] >= split_day]

    X_test = test[list(feature_names)]
    y_test = test["label"]

    result = permutation_importance(
        registry.model, X_test, y_test, n_repeats=5, random_state=42, scoring="roc_auc"
    )
    order = np.argsort(result.importances_mean)[::-1]
    return [feature_names[i] for i in order]


def _fraud_amount_tier_normalized(fraud_amount: float) -> float:
    for breakpoint, value in zip(cfg.FRAUD_AMOUNT_TIER_BREAKPOINTS, cfg.FRAUD_AMOUNT_TIER_VALUES):
        if fraud_amount <= breakpoint:
            return value
    return cfg.FRAUD_AMOUNT_TIER_VALUES[-1]


def _hours_since_complaint(complaint_day: int, now: datetime) -> float:
    epoch = datetime.fromisoformat(cfg.SYNTHETIC_DAY_ZERO_EPOCH)
    complaint_time = epoch + timedelta(days=complaint_day)
    delta_hours = (now - complaint_time).total_seconds() / 3600.0
    return max(0.0, delta_hours)


def compute_priority(ml_score: float, fraud_amount: float, complaint_day: int, now: datetime) -> Priority:
    amount_component = _fraud_amount_tier_normalized(fraud_amount)
    hours = _hours_since_complaint(complaint_day, now)
    urgency_component = min(hours / cfg.URGENCY_SATURATION_HOURS, 1.0)

    value = (
        cfg.PRIORITY_WEIGHT_ML * ml_score
        + cfg.PRIORITY_WEIGHT_AMOUNT * amount_component
        + cfg.PRIORITY_WEIGHT_URGENCY * urgency_component
    )
    value = min(max(value, 0.0), 1.0)

    level = next(band for lo, hi, band in cfg.RISK_BANDS if lo <= value < hi)

    return Priority(
        level=level,
        value=round(value, 6),
        method="heuristic_combination",
        formula_inputs=["ml_score", "fraud_amount_tier", "hours_since_complaint"],
    )


def compute_heuristic_score(features: dict[str, float]) -> float:
    hop_component = math.exp(-cfg.HEUR_HOP_DECAY_RATE * features["hop_distance"])
    passthrough_component = min(max(features["pass_through_ratio"], 0.0), 1.0)
    fanin_component = min(features["fan_in_recent_30d"] / cfg.HEUR_FANIN_CAP, 1.0)
    centrality_component = min(max(features["subgraph_degree_centrality"], 0.0), 1.0)

    score = (
        cfg.HEUR_WEIGHT_HOP * hop_component
        + cfg.HEUR_WEIGHT_PASSTHROUGH * passthrough_component
        + cfg.HEUR_WEIGHT_FANIN * fanin_component
        + cfg.HEUR_WEIGHT_CENTRALITY * centrality_component
    )
    return round(min(max(score, 0.0), 1.0), 6)


def _format_driver_value(feature: str, value: float) -> dict[str, str]:
    if feature in ("hop_distance", "fan_in_recent_30d", "out_degree_recent_30d", "account_age_days", "confirmed_history_count"):
        return {"value_int": str(int(round(value)))}
    return {"value_pct": f"{value * 100:.0f}%"}


def compute_drivers(features: dict[str, float], model: ModelARegistry) -> list[Driver]:
    ranking = _permutation_importance_ranking(tuple(model.feature_names_ordered))
    top_features = ranking[: cfg.DRIVER_TOP_N]
    drivers = []
    for feature in top_features:
        value = features[feature]
        template = cfg.DRIVER_TEMPLATES[feature]
        description = template.format(**_format_driver_value(feature, value))
        drivers.append(Driver(factor=feature, contribution=float(value), description=description))
    return drivers


def compute_risk_for_complaint(db: Session, model: ModelARegistry, complaint_id: int) -> list[RiskResult]:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise NoPredictionError(f"Complaint {complaint_id} not found")

    rows = (
        db.query(MuleChainPrediction)
        .filter(MuleChainPrediction.complaint_id == complaint_id)
        .order_by(MuleChainPrediction.rank)
        .all()
    )
    if not rows:
        raise NoPredictionError(
            f"No Model A prediction exists yet for complaint {complaint_id}. "
            f"POST /api/v1/predictions/run first."
        )

    now = datetime.now(timezone.utc)
    results = []
    for row in rows:
        priority = compute_priority(row.model_score, complaint.fraud_amount, complaint.day, now)
        heuristic = compute_heuristic_score(row.features)
        drivers = compute_drivers(row.features, model)
        results.append(
            RiskResult(
                complaint_id=complaint_id,
                account_id=row.candidate_account_id,
                ml_score=row.model_score,
                heuristic_score=heuristic,
                priority=priority,
                drivers=drivers,
                generated_at=now,
            )
        )
    return results
