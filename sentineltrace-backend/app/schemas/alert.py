import uuid
from datetime import datetime

from pydantic import BaseModel


class AlertOut(BaseModel):
    alert_id: uuid.UUID
    complaint_id: int
    account_id: int
    risk_score_id: uuid.UUID
    rank: int
    alert_type: str
    severity: str
    status: str
    priority_score: float          # Stage 5's own value. NOT a probability. NOT Model A's ml_score.
    risk_priority_value: float     # Stage 4's priority.value, copied verbatim for transparency.
    title: str
    explanation: str
    model_version: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    complaint_id: int
    results: list[AlertOut]


class AlertQueueResponse(BaseModel):
    results: list[AlertOut]
