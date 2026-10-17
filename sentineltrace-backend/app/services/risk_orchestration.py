"""
Risk + intervention window persistence orchestration (Stage 4).

Follows the exact same atomicity/concurrency pattern established and
validated in Stage 3B's app.services.mule_chain_prediction.run_prediction:
"replace current" strategy, wrapped in an explicit try/except with
rollback, serialized per-complaint via a PostgreSQL advisory lock. Risk
scores and the intervention window are persisted together in ONE
transaction, so a failure partway through can never leave one written
without the other.
"""
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.models.intervention import InterventionWindowRecord
from app.models.risk import RiskScore
from app.services import intervention_engine, risk_engine
from app.services.model_a import ModelARegistry


def compute_and_persist(db: Session, model: ModelARegistry, complaint_id: int) -> tuple[list[risk_engine.RiskResult], intervention_engine.InterventionWindow]:
    # Raises risk_engine.NoPredictionError / intervention_engine.NoPredictionError
    # (both simple RuntimeError subclasses) if no Model A prediction exists yet
    # for this complaint — computed BEFORE acquiring the lock or touching the
    # database for writes, so a failed precondition never begins a transaction.
    risk_results = risk_engine.compute_risk_for_complaint(db, model, complaint_id)
    intervention = intervention_engine.compute_intervention_window(db, complaint_id)

    try:
        # Same per-complaint advisory lock used in Stage 3B, reused here so a
        # concurrent POST /predictions/run and POST /risk for the same
        # complaint (or two concurrent POST /risk calls) cannot interleave.
        db.execute(text("SELECT pg_advisory_xact_lock(:complaint_id)"), {"complaint_id": complaint_id})

        db.execute(delete(RiskScore).where(RiskScore.complaint_id == complaint_id))
        db.execute(delete(InterventionWindowRecord).where(InterventionWindowRecord.complaint_id == complaint_id))

        risk_rows = []
        for r in risk_results:
            row = RiskScore(
                complaint_id=r.complaint_id,
                account_id=r.account_id,
                ml_score=r.ml_score,
                heuristic_score=r.heuristic_score,
                priority_level=r.priority.level,
                priority_value=r.priority.value,
                priority_method=r.priority.method,
                drivers=[{"factor": d.factor, "contribution": d.contribution, "description": d.description} for d in r.drivers],
            )
            db.add(row)
            risk_rows.append(row)

        intervention_row = InterventionWindowRecord(
            complaint_id=intervention.complaint_id,
            account_id=intervention.account_id,
            request_time=intervention.current_time,
            predicted_cashout_time=intervention.predicted_cashout_time,
            estimated_window_minutes=intervention.estimated_window_minutes,
            method=intervention.method,
            validation_status=intervention.validation_status,
            rationale=intervention.rationale,
        )
        db.add(intervention_row)

        db.commit()
    except Exception:
        db.rollback()
        raise

    return risk_results, intervention


def get_persisted_risk(db: Session, complaint_id: int) -> list[RiskScore] | None:
    rows = (
        db.query(RiskScore)
        .filter(RiskScore.complaint_id == complaint_id)
        .order_by(RiskScore.priority_value.desc())
        .all()
    )
    return list(rows) if rows else None


def get_persisted_intervention(db: Session, complaint_id: int) -> InterventionWindowRecord | None:
    return (
        db.query(InterventionWindowRecord)
        .filter(InterventionWindowRecord.complaint_id == complaint_id)
        .order_by(InterventionWindowRecord.generated_at.desc())
        .first()
    )
