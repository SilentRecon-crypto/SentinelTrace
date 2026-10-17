"""
Alert persistence orchestration (Stage 5).

Follows the exact same "replace current" + PostgreSQL advisory lock pattern
already established in Stage 3B (app.services.mule_chain_prediction) and
Stage 4 (app.services.risk_orchestration): each generation request for a
given complaint_id deletes any existing alert rows for that complaint_id,
then inserts a fresh set inside one transaction. This means:

  - repeated generation is idempotent (same risk/intervention state in ->
    same set of logical alerts out, no accumulation)
  - no duplicate "current" alerts for the same logical alert
    (complaint_id, account_id, alert_type)
  - a failure partway through rolls back cleanly, never leaving a partial
    alert set persisted

LIMITATION (documented, not hidden): because this is "replace current" and
Stage 5 does not implement a status-mutation endpoint, any status change
an investigator made in a future stage would be reset to "open" on
regeneration. This is acceptable for Stage 5's scope (no case-management
workflow yet) and is called out again in the README/final report.

Reuses the SAME advisory lock key (complaint_id) as Stage 4's
risk_orchestration.compute_and_persist, so alert generation for a complaint
can never interleave with a concurrent risk recomputation for that same
complaint.
"""
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.services import alert_engine


def compute_and_persist(db: Session, complaint_id: int) -> list[alert_engine.AlertResult]:
    # Raises alert_engine.NoRiskScoreError if no Stage 4 risk score exists yet
    # for this complaint — computed BEFORE acquiring the lock or touching the
    # database for writes, so a failed precondition never begins a transaction.
    alert_results = alert_engine.compute_alerts_for_complaint(db, complaint_id)

    try:
        db.execute(text("SELECT pg_advisory_xact_lock(:complaint_id)"), {"complaint_id": complaint_id})

        db.execute(delete(Alert).where(Alert.complaint_id == complaint_id))

        for r in alert_results:
            db.add(
                Alert(
                    complaint_id=r.complaint_id,
                    account_id=r.account_id,
                    risk_score_id=r.risk_score_id,
                    rank=r.rank,
                    alert_type=r.alert_type,
                    severity=r.severity,
                    status=r.status,
                    priority_score=r.priority_score,
                    risk_priority_value=r.risk_priority_value,
                    title=r.title,
                    explanation=r.explanation,
                    model_version=r.model_version,
                )
            )

        db.commit()
    except Exception:
        db.rollback()
        raise

    return alert_results


def get_persisted_alerts(db: Session, complaint_id: int) -> list[Alert]:
    """Returns the currently persisted alerts for a complaint, always as a
    list (never None) — an empty list is a legitimate outcome (no candidate
    for this complaint crossed the alert trigger threshold) and must not be
    conflated with "generation was never run". See app/api/alerts.py for
    how the 404-vs-200 decision is made (on complaint existence only, not
    on alert row count) — this was a Stage 5 static-audit fix; see that
    module's docstring and README "Stage 5 static audit" section.
    """
    rows = (
        db.query(Alert)
        .filter(Alert.complaint_id == complaint_id)
        .order_by(
            Alert.priority_score.desc(),
            Alert.risk_priority_value.desc(),
            Alert.rank.asc(),
            Alert.account_id.asc(),
        )
        .all()
    )
    return list(rows)


def get_alert_queue(db: Session, limit: int = 100) -> list[Alert]:
    """Deterministic prioritized alert queue across ALL complaints (§13):
    1. alert priority_score (Stage 5's own value) desc
    2. Stage 4 risk_priority_value desc
    3. Model A rank asc (lower rank = stronger candidate)
    4. complaint_id, account_id asc (final deterministic tie-breaker)
    Never relies on database default/insertion ordering.
    """
    return (
        db.query(Alert)
        .order_by(
            Alert.priority_score.desc(),
            Alert.risk_priority_value.desc(),
            Alert.rank.asc(),
            Alert.complaint_id.asc(),
            Alert.account_id.asc(),
        )
        .limit(limit)
        .all()
    )
