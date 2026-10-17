"""
Resolution engine (Stage 8).

Read-only with respect to Stages 1-7: only ever reads Case (via
app.services.case_engine.get_case/CaseNotFoundError, reused not
reimplemented) to check its status; never writes to Case or any other
Stage 1-7 table. Never calls candidate_generation, mule_chain_prediction,
risk_engine, risk_orchestration, intervention_engine, alert_engine,
alert_orchestration, case_engine's mutation functions, or evidence_engine.

CRITICAL BOUNDARY (see app/core/resolution_config.py for the full note):
this module builds and populates the case_resolutions table only. It does
NOT read from or write to `confirmed_history_count`, Model A features,
predictions, or risk calculation, and does not import anything from
candidate_generation.py or risk_engine.py.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import resolution_config as cfg
from app.models.case_resolution import CaseResolution
from app.services.case_engine import CaseNotFoundError, get_case  # reused, not reimplemented


class InvalidOutcomeTypeError(RuntimeError):
    """Raised for an outcome_type outside the authorized closed set. Maps to HTTP 422."""


class CaseNotResolvedError(RuntimeError):
    """Raised when a resolution is requested for a case whose status is not
    exactly 'resolved'. Maps to HTTP 409."""

    def __init__(self, current_status: str):
        self.current_status = current_status
        super().__init__(
            f"A resolution can only be recorded for a case with status "
            f"'{cfg.REQUIRED_CASE_STATUS}'; this case's current status is '{current_status}'."
        )


class DuplicateResolutionError(RuntimeError):
    """Raised when a resolution already exists for this case (one-per-case,
    immutable). Maps to HTTP 409."""

    def __init__(self, existing_resolution_id):
        self.existing_resolution_id = existing_resolution_id
        super().__init__(f"A resolution already exists for this case: {existing_resolution_id}")


class ResolutionNotFoundError(RuntimeError):
    """Raised when GET is requested for a case that exists but has no
    resolution recorded yet. Maps to HTTP 404 (a genuinely-absent record,
    not a legitimate-empty-result situation like Stage 5's alerts)."""


@dataclass
class ResolutionInput:
    outcome_type: str
    resolution_note: str | None
    recorded_by: str


def create_resolution(db: Session, case_id, data: ResolutionInput) -> CaseResolution:
    """Raises CaseNotFoundError / CaseNotResolvedError / DuplicateResolutionError / InvalidOutcomeTypeError."""
    if data.outcome_type not in cfg.RESOLUTION_VALID_OUTCOME_TYPES:
        raise InvalidOutcomeTypeError(
            f"outcome_type must be one of {cfg.RESOLUTION_VALID_OUTCOME_TYPES}, got '{data.outcome_type}'"
        )

    case = get_case(db, case_id)  # raises CaseNotFoundError

    if case.status != cfg.REQUIRED_CASE_STATUS:
        raise CaseNotResolvedError(case.status)

    existing = db.query(CaseResolution).filter(CaseResolution.case_id == case_id).first()
    if existing is not None:
        raise DuplicateResolutionError(existing.resolution_id)

    row = CaseResolution(
        case_id=case.case_id,
        outcome_type=data.outcome_type,
        resolution_note=data.resolution_note,
        recorded_by=data.recorded_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_resolution(db: Session, case_id) -> CaseResolution:
    """Raises CaseNotFoundError if the case doesn't exist, ResolutionNotFoundError
    if the case exists but has no resolution recorded yet."""
    get_case(db, case_id)  # raises CaseNotFoundError

    resolution = db.query(CaseResolution).filter(CaseResolution.case_id == case_id).first()
    if resolution is None:
        raise ResolutionNotFoundError(f"No resolution recorded yet for case {case_id}")
    return resolution
