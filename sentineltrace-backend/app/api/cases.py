"""
Case API (Stage 6).

Endpoints (minimal, per the planning audit — no contract file exists to
specify an exact surface; see app/core/case_config.py):

  POST  /api/v1/alerts/{alert_id}/cases        — open a case from an alert
  GET   /api/v1/cases/{case_id}                — retrieve a case
  GET   /api/v1/cases                           — deterministic case queue
  PATCH /api/v1/cases/{case_id}                 — status transition and/or assignment
  POST  /api/v1/cases/{case_id}/notes           — append an investigator note
  GET   /api/v1/cases/{case_id}/notes           — retrieve notes for a case

No evidence/attachment endpoints (Stage 6 planning audit: explicitly
deferred, treated as a separate later concern).
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core import case_config as cfg
from app.core.dependencies import get_db
from app.schemas.case import (
    CaseListResponse,
    CaseNoteCreateRequest,
    CaseNoteListResponse,
    CaseNoteOut,
    CaseOut,
    CaseUpdateRequest,
)
from app.services import case_engine

logger = logging.getLogger("sentineltrace")

alerts_router = APIRouter(prefix="/alerts", tags=["cases"])
router = APIRouter(prefix="/cases", tags=["cases"])


@alerts_router.post("/{alert_id}/cases", response_model=CaseOut, status_code=201)
def open_case(alert_id: uuid.UUID, db: Session = Depends(get_db)) -> CaseOut:
    try:
        case = case_engine.open_case_for_alert(db, alert_id)
    except case_engine.AlertNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except case_engine.DuplicateCaseError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"{exc} Use GET /api/v1/cases/{exc.existing_case_id} to retrieve it.",
        ) from exc
    return CaseOut.model_validate(case)


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: uuid.UUID, db: Session = Depends(get_db)) -> CaseOut:
    try:
        case = case_engine.get_case(db, case_id)
    except case_engine.CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CaseOut.model_validate(case)


@router.get("", response_model=CaseListResponse)
def get_case_queue(db: Session = Depends(get_db), limit: int = Query(default=100, ge=1, le=1000)) -> CaseListResponse:
    rows = case_engine.get_case_queue(db, limit=limit)
    return CaseListResponse(results=[CaseOut.model_validate(r) for r in rows])


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(case_id: uuid.UUID, payload: CaseUpdateRequest, db: Session = Depends(get_db)) -> CaseOut:
    if payload.status is not None and payload.status not in cfg.CASE_VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"Invalid status '{payload.status}'. Must be one of {cfg.CASE_VALID_STATUSES}.")

    # Pydantic v2 tracks which fields were actually present in the request
    # body via model_fields_set, so an explicit `"assigned_to": null` (clear
    # the assignment) is distinguishable from omitting the field entirely
    # (leave it unchanged) — both otherwise parse to the same Python None.
    assigned_to_provided = "assigned_to" in payload.model_fields_set

    try:
        result = case_engine.update_case(
            db, case_id,
            new_status=payload.status,
            assigned_to=payload.assigned_to,
            assigned_to_provided=assigned_to_provided,
        )
    except case_engine.CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except case_engine.InvalidTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return CaseOut.model_validate(result.case)


@router.post("/{case_id}/notes", response_model=CaseNoteOut, status_code=201)
def add_note(case_id: uuid.UUID, payload: CaseNoteCreateRequest, db: Session = Depends(get_db)) -> CaseNoteOut:
    try:
        note = case_engine.add_note(db, case_id, author=payload.author, note_text=payload.note_text)
    except case_engine.CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CaseNoteOut.model_validate(note)


@router.get("/{case_id}/notes", response_model=CaseNoteListResponse)
def get_notes(case_id: uuid.UUID, db: Session = Depends(get_db)) -> CaseNoteListResponse:
    try:
        notes = case_engine.get_notes(db, case_id)
    except case_engine.CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CaseNoteListResponse(case_id=case_id, results=[CaseNoteOut.model_validate(n) for n in notes])
