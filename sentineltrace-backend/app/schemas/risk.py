from datetime import datetime

from pydantic import BaseModel


class DriverOut(BaseModel):
    factor: str
    contribution: float
    description: str


class PriorityOut(BaseModel):
    level: str
    value: float
    method: str
    formula_inputs: list[str]


class RiskScoreOut(BaseModel):
    complaint_id: int
    account_id: int
    ml_score: float
    heuristic_score: float
    priority: PriorityOut
    drivers: list[DriverOut]
    generated_at: datetime


class RiskListResponse(BaseModel):
    complaint_id: int
    results: list[RiskScoreOut]
