import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_model_a
from app.schemas.prediction import PredictionRunRequest, PredictionRunResponse
from app.services.candidate_generation import NoCandidatesError
from app.services.mule_chain_prediction import ComplaintNotFoundError, InvalidTopKError, run_prediction

logger = logging.getLogger("sentineltrace")

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("/run", response_model=PredictionRunResponse)
def run_predictions(request: PredictionRunRequest, db: Session = Depends(get_db), model=Depends(get_model_a)) -> PredictionRunResponse:
    try:
        result = run_prediction(db, model, request.complaint_id, request.top_k)
    except ComplaintNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidTopKError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NoCandidatesError as exc:
        # A legitimate outcome (BFS found nothing), not a server fault.
        return PredictionRunResponse(
            complaint_id=request.complaint_id,
            model_version=model.version,
            generated_at=datetime.now(timezone.utc),
            prediction_run_id=uuid.uuid4(),
            candidate_count=0,
            results=[],
        )
    except Exception:
        logger.exception("Unexpected error running Model A prediction for complaint_id=%s", request.complaint_id)
        raise HTTPException(status_code=500, detail="Prediction failed due to an internal error.") from None

    return PredictionRunResponse(
        complaint_id=result.complaint_id,
        model_version=result.model_version,
        generated_at=result.generated_at,
        prediction_run_id=result.prediction_run_id,
        candidate_count=result.candidate_count,
        results=[
            {
                "rank": r.rank,
                "candidate_account_id": r.candidate_account_id,
                "model_score": r.model_score,
                "hop_distance": r.hop_distance,
                "features": r.features,
                "explanation": r.explanation,
            }
            for r in result.results
        ],
    )
