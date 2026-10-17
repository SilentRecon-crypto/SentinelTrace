"""
Structured case evidence API (Stage 7).

  POST /api/v1/cases/{case_id}/evidence   — attach evidence (append-only, 201)
  GET  /api/v1/cases/{case_id}/evidence    — retrieve evidence, chronological order

No update/delete endpoint — evidence is immutable once attached (per
explicit authorization). This is a separate router from app/api/cases.py
(which is frozen, per the Stage 7 authorization message) — registered
additively in app/main.py.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.evidence import CaseEvidenceCreateRequest, CaseEvidenceListResponse, CaseEvidenceOut
from app.services import evidence_engine
from app.services.case_engine import CaseNotFoundError

logger = logging.getLogger("sentineltrace")

router = APIRouter(prefix="/cases", tags=["case-evidence"])


def _to_out(row) -> CaseEvidenceOut:
    return CaseEvidenceOut(
        evidence_id=row.evidence_id,
        case_id=row.case_id,
        evidence_type=row.EVIDENCE_TYPE,
        transaction_id=getattr(row, "transaction_id", None),
        prediction_id=getattr(row, "prediction_id", None),
        risk_score_id=getattr(row, "risk_score_id", None),
        driver_index=getattr(row, "driver_index", None),
        note=row.note,
        added_by=row.added_by,
        created_at=row.created_at,
    )


@router.post("/{case_id}/evidence", response_model=CaseEvidenceOut, status_code=201)
def add_evidence(case_id: uuid.UUID, payload: CaseEvidenceCreateRequest, db: Session = Depends(get_db)) -> CaseEvidenceOut:
    data = evidence_engine.EvidenceInput(
        evidence_type=payload.evidence_type,
        transaction_id=payload.transaction_id,
        prediction_id=payload.prediction_id,
        risk_score_id=payload.risk_score_id,
        driver_index=payload.driver_index,
        note=payload.note,
        added_by=payload.added_by,
    )
    try:
        row = evidence_engine.add_evidence(db, case_id, data)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except evidence_engine.ReferenceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except evidence_engine.InvalidEvidenceRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_out(row)


@router.get("/{case_id}/evidence", response_model=CaseEvidenceListResponse)
def get_evidence(case_id: uuid.UUID, db: Session = Depends(get_db)) -> CaseEvidenceListResponse:
    try:
        rows = evidence_engine.get_evidence(db, case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CaseEvidenceListResponse(case_id=case_id, results=[_to_out(r) for r in rows])
