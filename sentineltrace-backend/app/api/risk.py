import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_model_a
from app.models.complaint import Complaint
from app.schemas.intervention import InterventionWindowOut
from app.schemas.risk import DriverOut, PriorityOut, RiskListResponse, RiskScoreOut
from app.services import risk_orchestration
from app.services.intervention_engine import NoPredictionError as InterventionNoPredictionError
from app.services.intervention_engine import urgency_band
from app.services.risk_engine import NoPredictionError as RiskNoPredictionError

logger = logging.getLogger("sentineltrace")

router = APIRouter(prefix="/complaints", tags=["risk"])


def _risk_result_to_out(r) -> RiskScoreOut:
    return RiskScoreOut(
        complaint_id=r.complaint_id,
        account_id=r.account_id,
        ml_score=r.ml_score,
        heuristic_score=r.heuristic_score,
        priority=PriorityOut(level=r.priority.level, value=r.priority.value, method=r.priority.method, formula_inputs=r.priority.formula_inputs),
        drivers=[DriverOut(factor=d.factor, contribution=d.contribution, description=d.description) for d in r.drivers],
        generated_at=r.generated_at,
    )


def _risk_row_to_out(row) -> RiskScoreOut:
    return RiskScoreOut(
        complaint_id=row.complaint_id,
        account_id=row.account_id,
        ml_score=row.ml_score,
        heuristic_score=row.heuristic_score,
        priority=PriorityOut(level=row.priority_level, value=row.priority_value, method=row.priority_method, formula_inputs=["ml_score", "fraud_amount_tier", "hours_since_complaint"]),
        drivers=[DriverOut(**d) for d in row.drivers],
        generated_at=row.generated_at,
    )


@router.post("/{complaint_id}/risk", response_model=RiskListResponse)
def run_risk_and_intervention(complaint_id: int, db: Session = Depends(get_db), model=Depends(get_model_a)) -> RiskListResponse:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")

    try:
        risk_results, _intervention = risk_orchestration.compute_and_persist(db, model, complaint_id)
    except (RiskNoPredictionError, InterventionNoPredictionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        logger.exception("Unexpected error computing risk/intervention for complaint_id=%s", complaint_id)
        raise HTTPException(status_code=500, detail="Risk computation failed due to an internal error.") from None

    return RiskListResponse(complaint_id=complaint_id, results=[_risk_result_to_out(r) for r in risk_results])


@router.get("/{complaint_id}/risk", response_model=RiskListResponse)
def get_risk(complaint_id: int, db: Session = Depends(get_db)) -> RiskListResponse:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")

    rows = risk_orchestration.get_persisted_risk(db, complaint_id)
    if rows is None:
        raise HTTPException(
            status_code=404,
            detail=f"No risk score has been computed yet for complaint {complaint_id}. "
                   f"POST /api/v1/complaints/{complaint_id}/risk first.",
        )
    return RiskListResponse(complaint_id=complaint_id, results=[_risk_row_to_out(r) for r in rows])


@router.get("/{complaint_id}/intervention-window", response_model=InterventionWindowOut)
def get_intervention_window(complaint_id: int, db: Session = Depends(get_db)) -> InterventionWindowOut:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")

    row = risk_orchestration.get_persisted_intervention(db, complaint_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No intervention window has been computed yet for complaint {complaint_id}. "
                   f"POST /api/v1/complaints/{complaint_id}/risk first.",
        )
    return InterventionWindowOut(
        complaint_id=row.complaint_id,
        account_id=row.account_id,
        current_time=row.request_time,
        predicted_cashout_time=row.predicted_cashout_time,
        estimated_window_minutes=row.estimated_window_minutes,
        urgency=urgency_band(row.estimated_window_minutes),
        method=row.method,
        validation_status=row.validation_status,
        rationale=row.rationale,
    )
