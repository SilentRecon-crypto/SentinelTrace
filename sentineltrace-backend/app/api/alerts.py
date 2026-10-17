"""
Alert API (Stage 5).

Endpoints, deliberately minimal per Stage 5 brief §12 (no contract file was
found specifying an exact API surface — see app/core/alert_config.py):

  POST /api/v1/complaints/{complaint_id}/alerts/generate
      Generate (idempotent, replace-current) alerts for a complaint from
      its existing persisted Stage 4 risk/intervention output.

  GET  /api/v1/complaints/{complaint_id}/alerts
      Retrieve the currently persisted alerts for a complaint.

  GET  /api/v1/alerts/queue
      Retrieve the deterministic, cross-complaint prioritized alert queue.

No status-mutation endpoint is implemented (Stage 5 brief §10/§12: case
actions/investigation workflow are explicitly out of scope).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.complaint import Complaint
from app.schemas.alert import AlertListResponse, AlertOut, AlertQueueResponse
from app.services import alert_orchestration
from app.services.alert_engine import NoRiskScoreError

logger = logging.getLogger("sentineltrace")

router = APIRouter(prefix="/complaints", tags=["alerts"])
queue_router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alert_row_to_out(row) -> AlertOut:
    return AlertOut.model_validate(row)


@router.post("/{complaint_id}/alerts/generate", response_model=AlertListResponse)
def generate_alerts(complaint_id: int, db: Session = Depends(get_db)) -> AlertListResponse:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")

    try:
        alert_orchestration.compute_and_persist(db, complaint_id)
    except NoRiskScoreError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        logger.exception("Unexpected error generating alerts for complaint_id=%s", complaint_id)
        raise HTTPException(status_code=500, detail="Alert generation failed due to an internal error.") from None

    rows = alert_orchestration.get_persisted_alerts(db, complaint_id)
    return AlertListResponse(complaint_id=complaint_id, results=[_alert_row_to_out(r) for r in rows])


@router.get("/{complaint_id}/alerts", response_model=AlertListResponse)
def get_alerts(complaint_id: int, db: Session = Depends(get_db)) -> AlertListResponse:
    """Returns the currently persisted alerts for a complaint. Always 200
    with a (possibly empty) list once the complaint itself exists — an
    empty list is a legitimate outcome (no candidate crossed the alert
    trigger threshold, or generation has simply not been run yet) and is
    never distinguishable from, nor conflated with, an error state.

    STAGE 5 STATIC AUDIT FIX: this endpoint previously raised 404 whenever
    zero alert rows were persisted, on the assumption that zero rows always
    meant "generate was never called" (mirroring the Stage 4 risk/
    intervention 404 pattern). That assumption does not hold for alerts:
    unlike risk scoring, a legitimate alert-generation run can correctly
    produce zero rows (e.g. a complaint whose highest-ranked candidate is
    only medium priority). The old code could not tell that case apart from
    "never generated" and would incorrectly 404 with a misleading "generate
    first" message even though generation had already run correctly. Fixed
    by dropping the row-count-based 404 and 404ing only on complaint
    non-existence, which is the one case this endpoint can actually be
    sure about.
    """
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")

    rows = alert_orchestration.get_persisted_alerts(db, complaint_id)
    return AlertListResponse(complaint_id=complaint_id, results=[_alert_row_to_out(r) for r in rows])


@queue_router.get("/queue", response_model=AlertQueueResponse)
def get_alert_queue(db: Session = Depends(get_db), limit: int = Query(default=100, ge=1, le=1000)) -> AlertQueueResponse:
    rows = alert_orchestration.get_alert_queue(db, limit=limit)
    return AlertQueueResponse(results=[_alert_row_to_out(r) for r in rows])
