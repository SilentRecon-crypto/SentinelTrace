"""
Investigation dossier engine (Stage 9).

PURE READ-ONLY: this module performs exclusively db.get()/db.query() calls.
It contains NO db.add, db.commit, db.delete, no SQLAlchemy update()/
delete()/insert() construct, and calls no mutation function from any other
module. tests/test_dossier_api.py::test_dossier_engine_has_no_write_operations
proves this via AST inspection, not just by inspection here.

CRITICAL RELATIONSHIP RULE: every cross-stage association below is derived
from either (a) an actual persisted foreign key, or (b) the same
(complaint_id, account_id) equality-matching pattern this repository has
already established and relied on since Stage 7
(app/services/evidence_engine.py's relevance-invariant checks) — never an
association invented for this stage. Where no deterministic association
exists, the corresponding section is None and a plain-language reason is
appended to the dossier's `limitations` list rather than guessed at.

Relationship chain used:
  Case.alert_id            -> Alert.alert_id            (persisted FK, exact)
  Alert.risk_score_id      -> RiskScore.score_id         (persisted FK, exact)
  Case.complaint_id/account_id -> InterventionWindowRecord.complaint_id/account_id
                                   (equality match — InterventionWindowRecord has no FK
                                    to Case/Alert; only exists at all for the complaint's
                                    rank==1 candidate, per Stage 4's intervention_engine.py,
                                    so this section is legitimately absent for any
                                    non-top-ranked case's account)
  Case.complaint_id/account_id -> MuleChainPrediction.complaint_id/candidate_account_id
                                   (equality match — MuleChainPrediction has no FK to
                                    Case/Alert either; same pattern Stage 7 already uses
                                    to validate graph_explanation_reference evidence)

Reuses read functions from case_engine/evidence_engine/resolution_engine
rather than reimplementing their queries, and reuses the exact risk/
intervention response-construction logic already in app/api/risk.py rather
than duplicating it.
"""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.case import Case
from app.models.intervention import InterventionWindowRecord
from app.models.prediction import MuleChainPrediction
from app.models.risk import RiskScore
from app.services import case_engine, evidence_engine
from app.services import resolution_engine as res_engine
from app.services.case_engine import CaseNotFoundError  # reused, not reimplemented
from app.services.intervention_engine import urgency_band  # reused, not reimplemented


@dataclass
class DossierResult:
    case: Case
    notes: list
    evidence: list
    resolution: object | None
    alert: Alert | None
    risk: RiskScore | None
    intervention_row: InterventionWindowRecord | None
    intervention_urgency: str | None
    prediction: MuleChainPrediction | None
    limitations: list[str] = field(default_factory=list)


def _find_intervention(db: Session, case: Case) -> InterventionWindowRecord | None:
    """Mirrors app/services/alert_engine.py's own established pattern for
    locating the (at most one) intervention row for a complaint and
    confirming it actually belongs to this case's account before using it."""
    row = (
        db.query(InterventionWindowRecord)
        .filter(InterventionWindowRecord.complaint_id == case.complaint_id)
        .order_by(InterventionWindowRecord.generated_at.desc())
        .first()
    )
    if row is not None and row.account_id == case.account_id:
        return row
    return None


def _find_prediction(db: Session, case: Case) -> MuleChainPrediction | None:
    """(complaint_id, account_id) equality match — the same pattern
    app/services/evidence_engine.py already uses to validate
    graph_explanation_reference evidence. Ordered by created_at desc as a
    defensive tie-breaker in case more than one row somehow matches (should
    not happen given Stage 3A's replace-current uniqueness-per-account
    invariant, but this dossier never assumes it without a check)."""
    return (
        db.query(MuleChainPrediction)
        .filter(
            MuleChainPrediction.complaint_id == case.complaint_id,
            MuleChainPrediction.candidate_account_id == case.account_id,
        )
        .order_by(MuleChainPrediction.created_at.desc())
        .first()
    )


def build_dossier(db: Session, case_id) -> DossierResult:
    """Raises CaseNotFoundError if the case doesn't exist. Never writes
    anything; never mutates any argument's persisted state."""
    case = case_engine.get_case(db, case_id)  # raises CaseNotFoundError

    notes = case_engine.get_notes(db, case_id)
    evidence = evidence_engine.get_evidence(db, case_id)

    try:
        resolution = res_engine.get_resolution(db, case_id)
    except res_engine.ResolutionNotFoundError:
        resolution = None

    limitations: list[str] = []

    alert = db.get(Alert, case.alert_id)
    if alert is None:
        # Should not occur given case.alert_id's NOT NULL FK to alerts.alert_id,
        # but this dossier never assumes referential integrity without checking.
        limitations.append(
            f"Alert {case.alert_id} referenced by this case could not be found; "
            f"alert/risk/prediction sections are unavailable."
        )
        risk = None
        prediction = None
    else:
        risk = db.get(RiskScore, alert.risk_score_id)
        if risk is None:
            limitations.append(
                f"RiskScore {alert.risk_score_id} referenced by this case's alert could not be found."
            )
        prediction = _find_prediction(db, case)
        if prediction is None:
            limitations.append(
                f"No Model A prediction row currently matches complaint_id={case.complaint_id}, "
                f"account_id={case.account_id} (candidate_account_id). If Stage 3A predictions "
                f"were regenerated since this case was opened, the original prediction row may "
                f"have been replaced ('replace current' persistence, per Stage 3A)."
            )

    intervention_row = _find_intervention(db, case)
    intervention_urgency = urgency_band(intervention_row.estimated_window_minutes) if intervention_row is not None else None
    if intervention_row is None:
        limitations.append(
            f"No intervention window is available for account {case.account_id}: Stage 4's "
            f"intervention engine only computes a window for a complaint's rank==1 (top-ranked) "
            f"candidate, and/or none has been computed yet for complaint {case.complaint_id}."
        )

    return DossierResult(
        case=case,
        notes=notes,
        evidence=evidence,
        resolution=resolution,
        alert=alert,
        risk=risk,
        intervention_row=intervention_row,
        intervention_urgency=intervention_urgency,
        prediction=prediction,
        limitations=limitations,
    )
