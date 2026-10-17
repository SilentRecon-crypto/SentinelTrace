"""
Case engine (Stage 6).

Encapsulates all Case/CaseNote business logic so app/api/cases.py stays a
thin HTTP layer, mirroring the engine/orchestration split established in
Stage 5 (alert_engine.py + alert_orchestration.py) and Stage 4.

Unlike Stage 5's alerts (fully-derived, deterministically regenerable data),
a Case is investigator-authored state: it is created once from an Alert and
then mutated over time via explicit, validated transitions. There is no
"replace current" here — mutations are real, targeted UPDATEs, and repeated
identical requests are safe (idempotent) precisely because illegal/no-op
transitions are rejected rather than silently reapplied.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import case_config as cfg
from app.models.alert import Alert
from app.models.case import Case, CaseNote


class AlertNotFoundError(RuntimeError):
    """Raised when a case is requested/created for an alert_id that doesn't exist."""


class DuplicateCaseError(RuntimeError):
    """Raised when a case already exists for the given alert_id."""

    def __init__(self, existing_case_id):
        self.existing_case_id = existing_case_id
        super().__init__(f"A case already exists for this alert: {existing_case_id}")


class CaseNotFoundError(RuntimeError):
    """Raised when a case_id does not exist."""


class InvalidTransitionError(RuntimeError):
    """Raised when a requested status transition is not permitted from the case's current status."""

    def __init__(self, current_status: str, requested_status: str):
        self.current_status = current_status
        self.requested_status = requested_status
        super().__init__(
            f"Cannot transition case from '{current_status}' to '{requested_status}'. "
            f"Legal transitions from '{current_status}': "
            f"{cfg.CASE_STATUS_TRANSITIONS.get(current_status, [])}"
        )


@dataclass
class CaseUpdateResult:
    case: Case
    changed: bool


def open_case_for_alert(db: Session, alert_id) -> Case:
    """Create a case from an existing alert. Raises AlertNotFoundError if the
    alert doesn't exist, DuplicateCaseError if a case already exists for it
    (case creation is a deliberate human action, not derived/regenerable
    data — Stage 6 does not silently overwrite or return prior investigator
    state the way Stage 5's alert regeneration replaces derived rows)."""
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise AlertNotFoundError(f"Alert {alert_id} not found")

    existing = db.query(Case).filter(Case.alert_id == alert_id).first()
    if existing is not None:
        raise DuplicateCaseError(existing.case_id)

    case = Case(
        alert_id=alert.alert_id,
        complaint_id=alert.complaint_id,
        account_id=alert.account_id,
        status=cfg.CASE_STATUS_DEFAULT,
        assigned_to=None,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def get_case(db: Session, case_id) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(f"Case {case_id} not found")
    return case


def update_case(db: Session, case_id, new_status: str | None, assigned_to: str | None, assigned_to_provided: bool) -> CaseUpdateResult:
    """Apply an optional status transition and/or assignment change.

    - new_status=None means "no status change requested".
    - assigned_to_provided distinguishes "the request body omitted
      assigned_to" (leave unchanged) from "the request body explicitly set
      assigned_to to null/a value" (apply it, including clearing it).
    Raises CaseNotFoundError / InvalidTransitionError as appropriate. Both
    changes are applied in one transaction — if the status transition is
    illegal, nothing is written, including the assignment change.
    """
    case = get_case(db, case_id)
    changed = False

    if new_status is not None and new_status != case.status:
        legal_next = cfg.CASE_STATUS_TRANSITIONS.get(case.status, [])
        if new_status not in legal_next:
            raise InvalidTransitionError(case.status, new_status)
        case.status = new_status
        changed = True

    if assigned_to_provided and assigned_to != case.assigned_to:
        case.assigned_to = assigned_to
        changed = True

    if changed:
        db.commit()
        db.refresh(case)

    return CaseUpdateResult(case=case, changed=changed)


def add_note(db: Session, case_id, author: str, note_text: str) -> CaseNote:
    case = get_case(db, case_id)  # raises CaseNotFoundError if missing
    note = CaseNote(case_id=case.case_id, author=author, note_text=note_text)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_notes(db: Session, case_id) -> list[CaseNote]:
    get_case(db, case_id)  # raises CaseNotFoundError if missing
    return (
        db.query(CaseNote)
        .filter(CaseNote.case_id == case_id)
        .order_by(CaseNote.created_at.asc())
        .all()
    )


def get_case_queue(db: Session, limit: int = 100) -> list[Case]:
    """Deterministic case queue: open/investigating/escalated surfaced before
    resolved (app.core.case_config.CASE_STATUS_QUEUE_RANK), then most
    recently updated first, then case_id as a final deterministic
    tie-breaker. Never relies on database default/insertion ordering."""
    rows = db.query(Case).all()
    rows.sort(
        key=lambda c: (
            cfg.CASE_STATUS_QUEUE_RANK.get(c.status, len(cfg.CASE_STATUS_QUEUE_RANK)),
            -c.updated_at.timestamp(),
            str(c.case_id),
        )
    )
    return rows[:limit]
