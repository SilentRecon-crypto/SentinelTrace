from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PredictionRunRequest(BaseModel):
    complaint_id: int
    top_k: int = Field(default=5, ge=1, le=50)


class RankedCandidateOut(BaseModel):
    rank: int
    candidate_account_id: int
    model_score: float = Field(..., description="P(is_mule_account), the raw Model A output. Not a risk score, confidence, or cash-out probability.")
    hop_distance: int
    features: dict[str, float]
    explanation: list[str]


class PredictionRunResponse(BaseModel):
    complaint_id: int
    model_version: str
    generated_at: datetime
    prediction_run_id: UUID
    candidate_count: int
    results: list[RankedCandidateOut]
