from datetime import datetime

from pydantic import BaseModel


class InterventionWindowOut(BaseModel):
    complaint_id: int
    account_id: int
    current_time: datetime
    predicted_cashout_time: datetime
    estimated_window_minutes: int
    urgency: str
    method: str
    validation_status: str
    rationale: str
