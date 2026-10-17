"""
Investigation dossier API (Stage 9).

  GET /api/v1/cases/{case_id}/dossier   — read-only composed view (200; 404 if case missing)

No POST/PUT/PATCH/DELETE. Read-only reuse of:
  - app.api.evidence._to_out for CaseEvidenceOut construction (the evidence
    section MUST use the exact same representation as the standalone
    GET /cases/{case_id}/evidence endpoint — the three normalized Stage 7
    ORM classes carry their type as a plain class attribute `EVIDENCE_TYPE`,
    not a field named `evidence_type`, so CaseEvidenceOut.model_validate()
    cannot be called directly on them; _to_out already handles this
    correctly and is reused here rather than reimplemented)
  - app.api.risk._risk_row_to_out for RiskScoreOut construction (identical
    mapping already established there — not duplicated)
  - app.services.intervention_engine.urgency_band for the intervention
    section, exactly as app/api/risk.py itself does
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.evidence import _to_out as _evidence_row_to_out  # reused, not reimplemented — see fix note below
from app.core.dependencies import get_db
from app.schemas.alert import AlertOut
from app.schemas.case import CaseNoteOut, CaseOut
from app.schemas.dossier import DossierOut
from app.schemas.intervention import InterventionWindowOut
from app.schemas.prediction import RankedCandidateOut
from app.schemas.resolution import CaseResolutionOut
from app.services import dossier_engine
from app.services.case_engine import CaseNotFoundError

logger = logging.getLogger("sentineltrace")

router = APIRouter(prefix="/cases", tags=["dossier"])


@router.get("/{case_id}/dossier", response_model=DossierOut)
def get_dossier(case_id: uuid.UUID, db: Session = Depends(get_db)) -> DossierOut:
    try:
        result = dossier_engine.build_dossier(db, case_id)
    except CaseNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    risk_out = None
    if result.risk is not None:
        from app.api.risk import _risk_row_to_out  # reused, not reimplemented
        risk_out = _risk_row_to_out(result.risk)

    intervention_out = None
    if result.intervention_row is not None:
        row = result.intervention_row
        intervention_out = InterventionWindowOut(
            complaint_id=row.complaint_id,
            account_id=row.account_id,
            current_time=row.request_time,
            predicted_cashout_time=row.predicted_cashout_time,
            estimated_window_minutes=row.estimated_window_minutes,
            urgency=result.intervention_urgency,
            method=row.method,
            validation_status=row.validation_status,
            rationale=row.rationale,
        )

    prediction_out = None
    if result.prediction is not None:
        p = result.prediction
        prediction_out = RankedCandidateOut(
            rank=p.rank,
            candidate_account_id=p.candidate_account_id,
            model_score=p.model_score,
            hop_distance=p.hop_distance,
            features=p.features,
            explanation=p.explanation,
        )

    return DossierOut(
        case=CaseOut.model_validate(result.case),
        notes=[CaseNoteOut.model_validate(n) for n in result.notes],  # already chronological, per case_engine.get_notes
        evidence=[_evidence_row_to_out(e) for e in result.evidence],  # already chronological, per evidence_engine.get_evidence
        resolution=CaseResolutionOut.model_validate(result.resolution) if result.resolution is not None else None,
        alert=AlertOut.model_validate(result.alert) if result.alert is not None else None,
        risk=risk_out,
        intervention=intervention_out,
        prediction=prediction_out,
        limitations=result.limitations,
    )
