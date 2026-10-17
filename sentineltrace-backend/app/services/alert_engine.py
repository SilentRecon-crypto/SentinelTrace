"""
Alert engine (Stage 5).

Generates alerts purely from EXISTING, already-persisted Stage 4 outputs
(app.models.risk.RiskScore, app.models.intervention.InterventionWindowRecord)
and the existing Stage 3A rank (app.models.prediction.MuleChainPrediction).
This module does not call Model A, does not recompute ml_score,
heuristic_score, or priority.value, and does not touch the graph engine —
Stage 4 is a frozen input (Stage 5 brief §3, §6).

GROUND-TRUTH ISOLATION: reads only RiskScore, InterventionWindowRecord, and
MuleChainPrediction.rank/model_version — never complaints.chain, never
accounts.acc_type, never candidate.label. See tests/test_alert_engine.py
and tests/test_alert_api.py for automated leakage regression checks.

DETERMINISM: for a fixed set of persisted RiskScore/InterventionWindowRecord
rows and a fixed app.core.alert_config, compute_alerts_for_complaint always
returns the same alert_type/severity/priority_score/explanation/ordering.
No randomness, no wall-clock-dependent computation influences alert content
(created_at/updated_at are DB-assigned timestamps, not content).
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import alert_config as cfg
from app.core import risk_config as risk_cfg
from app.models.complaint import Complaint
from app.models.intervention import InterventionWindowRecord
from app.models.prediction import MuleChainPrediction
from app.models.risk import RiskScore
from app.services.intervention_engine import urgency_band


class NoRiskScoreError(RuntimeError):
    """Raised when alerts are requested for a complaint with no persisted Stage 4 risk score."""


@dataclass
class AlertResult:
    complaint_id: int
    account_id: int
    risk_score_id: object  # uuid.UUID
    rank: int
    alert_type: str
    severity: str
    status: str
    priority_score: float
    risk_priority_value: float
    title: str
    explanation: str
    model_version: str


def _urgency_component(estimated_window_minutes: int | None) -> float:
    """1.0 = maximally urgent (very short window), 0.0 = no urgency evidence
    available for this candidate (i.e. it isn't the rank==1 account that
    Stage 4's intervention engine computes a window for)."""
    if estimated_window_minutes is None:
        return 0.0
    fraction_elapsed_of_max = min(estimated_window_minutes / risk_cfg.INTERVENTION_MAX_MINUTES, 1.0)
    return round(1.0 - fraction_elapsed_of_max, 6)


def _priority_score(risk_priority_value: float, estimated_window_minutes: int | None) -> float:
    urgency = _urgency_component(estimated_window_minutes)
    value = (
        cfg.ALERT_PRIORITY_WEIGHT_RISK * risk_priority_value
        + cfg.ALERT_PRIORITY_WEIGHT_URGENCY * urgency
    )
    return round(min(max(value, 0.0), 1.0), 6)


def _build_explanation(risk_row: RiskScore, intervention_row: InterventionWindowRecord | None, alert_type: str) -> str:
    driver_descriptions = [d["description"] for d in risk_row.drivers[: cfg.ALERT_EXPLANATION_MAX_DRIVERS]]
    drivers_text = "; ".join(driver_descriptions) if driver_descriptions else "no individual drivers recorded"

    base = (
        f"{risk_row.priority_level.capitalize()} operational priority "
        f"(Stage 4 priority value {risk_row.priority_value:.2f}) driven by: {drivers_text}."
    )
    if alert_type == cfg.ALERT_TYPE_INTERVENTION_URGENCY and intervention_row is not None:
        band = urgency_band(intervention_row.estimated_window_minutes)
        base += (
            f" Estimated intervention window is {intervention_row.estimated_window_minutes} minute(s) "
            f"({band} urgency): {intervention_row.rationale}"
        )
    return base


def _build_title(account_id: int, severity: str, alert_type: str, intervention_row: InterventionWindowRecord | None) -> str:
    if alert_type == cfg.ALERT_TYPE_INTERVENTION_URGENCY and intervention_row is not None:
        return cfg.ALERT_TITLE_TEMPLATE_INTERVENTION.format(
            account_id=account_id, estimated_window_minutes=intervention_row.estimated_window_minutes
        )
    return cfg.ALERT_TITLE_TEMPLATE_MULE_CHAIN.format(account_id=account_id, severity=severity)


def compute_alerts_for_complaint(db: Session, complaint_id: int) -> list[AlertResult]:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise NoRiskScoreError(f"Complaint {complaint_id} not found")

    risk_rows = (
        db.query(RiskScore)
        .filter(RiskScore.complaint_id == complaint_id)
        .order_by(RiskScore.priority_value.desc())
        .all()
    )
    if not risk_rows:
        raise NoRiskScoreError(
            f"No Stage 4 risk score exists yet for complaint {complaint_id}. "
            f"POST /api/v1/complaints/{complaint_id}/risk first."
        )

    # rank + model_version, keyed by account_id (existing Stage 3A output, read-only).
    prediction_rows = (
        db.query(MuleChainPrediction)
        .filter(MuleChainPrediction.complaint_id == complaint_id)
        .all()
    )
    rank_by_account = {p.candidate_account_id: p.rank for p in prediction_rows}
    model_version_by_account = {p.candidate_account_id: p.model_version for p in prediction_rows}

    intervention_row = (
        db.query(InterventionWindowRecord)
        .filter(InterventionWindowRecord.complaint_id == complaint_id)
        .order_by(InterventionWindowRecord.generated_at.desc())
        .first()
    )

    results: list[AlertResult] = []
    for risk_row in risk_rows:
        if risk_row.priority_level not in cfg.ALERT_TRIGGERING_PRIORITY_LEVELS:
            continue

        rank = rank_by_account.get(risk_row.account_id)
        model_version = model_version_by_account.get(risk_row.account_id, "unknown")

        is_intervention_account = (
            intervention_row is not None and intervention_row.account_id == risk_row.account_id
        )
        applicable_intervention = intervention_row if is_intervention_account else None

        alert_type = cfg.ALERT_TYPE_MULE_CHAIN
        if (
            applicable_intervention is not None
            and urgency_band(applicable_intervention.estimated_window_minutes) in cfg.ALERT_INTERVENTION_URGENCY_TRIGGER_BANDS
        ):
            alert_type = cfg.ALERT_TYPE_INTERVENTION_URGENCY

        estimated_window_minutes = (
            applicable_intervention.estimated_window_minutes if applicable_intervention is not None else None
        )
        priority_score = _priority_score(risk_row.priority_value, estimated_window_minutes)
        title = _build_title(risk_row.account_id, risk_row.priority_level, alert_type, applicable_intervention)
        explanation = _build_explanation(risk_row, applicable_intervention, alert_type)

        results.append(
            AlertResult(
                complaint_id=complaint_id,
                account_id=risk_row.account_id,
                risk_score_id=risk_row.score_id,
                rank=rank if rank is not None else 0,
                alert_type=alert_type,
                severity=risk_row.priority_level,
                status=cfg.ALERT_STATUS_DEFAULT,
                priority_score=priority_score,
                risk_priority_value=risk_row.priority_value,
                title=title,
                explanation=explanation,
                model_version=model_version,
            )
        )

    return results
