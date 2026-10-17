"""
Evidence engine (Stage 7).

Read-only with respect to Stages 1-6: this module only ever calls db.get()/
db.query() against Transaction, MuleChainPrediction, RiskScore, and Case —
it never writes to any of those tables, never calls candidate_generation,
mule_chain_prediction, risk_engine, risk_orchestration, intervention_engine,
alert_engine, alert_orchestration, or case_engine's mutation functions. It
imports exactly one symbol from case_engine (CaseNotFoundError) to avoid
defining a second "case not found" concept.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import evidence_config as cfg
from app.models.case import Case
from app.models.evidence import CaseEvidenceGraphExplanation, CaseEvidenceRiskDriver, CaseEvidenceTransaction
from app.models.prediction import MuleChainPrediction
from app.models.risk import RiskScore
from app.models.transaction import Transaction
from app.services.case_engine import CaseNotFoundError, get_case  # reused, not reimplemented

EvidenceRow = CaseEvidenceTransaction | CaseEvidenceGraphExplanation | CaseEvidenceRiskDriver


class InvalidEvidenceRequestError(RuntimeError):
    """Raised for: unknown evidence_type, wrong/missing fields for the given
    type, a driver_index out of bounds, or a reference that exists but does
    not satisfy the complaint/account relevance invariant documented in
    app/core/evidence_config.py. Maps to HTTP 422."""


class ReferenceNotFoundError(RuntimeError):
    """Raised when the referenced transaction/prediction/risk score does not
    exist at all. Maps to HTTP 404. Distinct from InvalidEvidenceRequestError
    (exists but irrelevant to this case) and from CaseNotFoundError."""


@dataclass
class EvidenceInput:
    evidence_type: str
    transaction_id: int | None
    prediction_id: int | None
    risk_score_id: object | None  # uuid.UUID | None
    driver_index: int | None
    note: str | None
    added_by: str


def _add_transaction_evidence(db: Session, case: Case, data: EvidenceInput) -> CaseEvidenceTransaction:
    if data.transaction_id is None or data.prediction_id is not None or data.risk_score_id is not None or data.driver_index is not None:
        raise InvalidEvidenceRequestError(
            f"evidence_type '{cfg.EVIDENCE_TYPE_TRANSACTION}' requires exactly transaction_id "
            f"and none of prediction_id/risk_score_id/driver_index."
        )
    txn = db.get(Transaction, data.transaction_id)
    if txn is None:
        raise ReferenceNotFoundError(f"Transaction {data.transaction_id} not found")
    if txn.src_account_id != case.account_id and txn.dst_account_id != case.account_id:
        raise InvalidEvidenceRequestError(
            f"Transaction {data.transaction_id} does not involve case account {case.account_id} "
            f"(src={txn.src_account_id}, dst={txn.dst_account_id})."
        )
    return CaseEvidenceTransaction(case_id=case.case_id, transaction_id=data.transaction_id, note=data.note, added_by=data.added_by)


def _add_graph_explanation_evidence(db: Session, case: Case, data: EvidenceInput) -> CaseEvidenceGraphExplanation:
    if data.prediction_id is None or data.transaction_id is not None or data.risk_score_id is not None or data.driver_index is not None:
        raise InvalidEvidenceRequestError(
            f"evidence_type '{cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION}' requires exactly prediction_id "
            f"and none of transaction_id/risk_score_id/driver_index."
        )
    prediction = db.get(MuleChainPrediction, data.prediction_id)
    if prediction is None:
        raise ReferenceNotFoundError(f"Prediction {data.prediction_id} not found")
    if prediction.complaint_id != case.complaint_id or prediction.candidate_account_id != case.account_id:
        raise InvalidEvidenceRequestError(
            f"Prediction {data.prediction_id} (complaint_id={prediction.complaint_id}, "
            f"candidate_account_id={prediction.candidate_account_id}) does not match this case's "
            f"complaint_id={case.complaint_id}/account_id={case.account_id}."
        )
    return CaseEvidenceGraphExplanation(case_id=case.case_id, prediction_id=data.prediction_id, note=data.note, added_by=data.added_by)


def _add_risk_driver_evidence(db: Session, case: Case, data: EvidenceInput) -> CaseEvidenceRiskDriver:
    if data.risk_score_id is None or data.transaction_id is not None or data.prediction_id is not None:
        raise InvalidEvidenceRequestError(
            f"evidence_type '{cfg.EVIDENCE_TYPE_RISK_DRIVER}' requires exactly risk_score_id "
            f"(driver_index optional) and none of transaction_id/prediction_id."
        )
    risk = db.get(RiskScore, data.risk_score_id)
    if risk is None:
        raise ReferenceNotFoundError(f"RiskScore {data.risk_score_id} not found")
    if risk.complaint_id != case.complaint_id or risk.account_id != case.account_id:
        raise InvalidEvidenceRequestError(
            f"RiskScore {data.risk_score_id} (complaint_id={risk.complaint_id}, account_id={risk.account_id}) "
            f"does not match this case's complaint_id={case.complaint_id}/account_id={case.account_id}."
        )
    if data.driver_index is not None and not (0 <= data.driver_index < len(risk.drivers)):
        raise InvalidEvidenceRequestError(
            f"driver_index {data.driver_index} out of range for RiskScore {data.risk_score_id} "
            f"which has {len(risk.drivers)} driver(s)."
        )
    return CaseEvidenceRiskDriver(
        case_id=case.case_id, risk_score_id=data.risk_score_id, driver_index=data.driver_index,
        note=data.note, added_by=data.added_by,
    )


_HANDLERS = {
    cfg.EVIDENCE_TYPE_TRANSACTION: _add_transaction_evidence,
    cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION: _add_graph_explanation_evidence,
    cfg.EVIDENCE_TYPE_RISK_DRIVER: _add_risk_driver_evidence,
}


def add_evidence(db: Session, case_id, data: EvidenceInput) -> EvidenceRow:
    """Raises CaseNotFoundError / InvalidEvidenceRequestError / ReferenceNotFoundError."""
    case = get_case(db, case_id)  # raises CaseNotFoundError

    handler = _HANDLERS.get(data.evidence_type)
    if handler is None:
        raise InvalidEvidenceRequestError(f"Unknown evidence_type '{data.evidence_type}'. Must be one of {cfg.EVIDENCE_VALID_TYPES}.")

    row = handler(db, case, data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_evidence(db: Session, case_id) -> list[EvidenceRow]:
    """Raises CaseNotFoundError if the case doesn't exist. Returns evidence
    from all three tables, merged and ordered chronologically (created_at
    asc, evidence_id as a deterministic tie-breaker) — never relies on
    per-table insertion order or a UNION's arbitrary ordering."""
    get_case(db, case_id)  # raises CaseNotFoundError

    txn_rows = db.query(CaseEvidenceTransaction).filter(CaseEvidenceTransaction.case_id == case_id).all()
    graph_rows = db.query(CaseEvidenceGraphExplanation).filter(CaseEvidenceGraphExplanation.case_id == case_id).all()
    risk_rows = db.query(CaseEvidenceRiskDriver).filter(CaseEvidenceRiskDriver.case_id == case_id).all()

    combined: list[EvidenceRow] = [*txn_rows, *graph_rows, *risk_rows]
    combined.sort(key=lambda r: (r.created_at, str(r.evidence_id)))
    return combined
