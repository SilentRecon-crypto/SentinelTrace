"""
Case resolution API (Stage 8).

  POST /api/v1/cases/{case_id}/resolution   — record the case outcome (immutable, one per case)
  GET  /api/v1/cases/{case_id}/resolution    — retrieve it

No PATCH/DELETE anywhere — a resolution is immutable once recorded. This is
a separate router from app/api/cases.py (frozen, per Stage 8 authorization)
and from app/api/evidence.py (also frozen) — registered additively in
app/main.py.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.schemas.resolution import CaseResolutionCreateRequest, CaseResolutionOut
from app.services import resolution_engine
from app.services.case_engine import CaseNotFoundError

logger = logging.getLogger("sentineltrace")

router = APIRouter(prefix="/cases", tags=["case-resolution"])


@router.post("/{case_id}/resolution", response_model=CaseResolutionOut, status_code=201)
def create_resolution(case_id: uuid.UUID, payload: CaseResolutionCreateRequest, db: Session = Depends(get_db)) -> CaseResolutionOut:
    data = resolution_engine.ResolutionInput(
        outcome_type=payload.outcome_type,
        resolution_note=payload.resolution_note,
        recorded_by=payload.recorded_by,
    )
    try:
        row = resolution_engine.create_resolution(db, case_id, data)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except resolution_engine.CaseNotResolvedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except resolution_engine.DuplicateResolutionError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} Use GET /api/v1/cases/{case_id}/resolution to retrieve it.",
        ) from exc
    except resolution_engine.InvalidOutcomeTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CaseResolutionOut.model_validate(row)


@router.get("/{case_id}/resolution", response_model=CaseResolutionOut)
def get_resolution(case_id: uuid.UUID, db: Session = Depends(get_db)) -> CaseResolutionOut:
    try:
        row = resolution_engine.get_resolution(db, case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except resolution_engine.ResolutionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CaseResolutionOut.model_validate(row)
