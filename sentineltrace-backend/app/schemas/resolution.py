import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.core import resolution_config as cfg


class CaseResolutionCreateRequest(BaseModel):
    outcome_type: str = Field(description=f"One of {cfg.RESOLUTION_VALID_OUTCOME_TYPES}")
    resolution_note: str | None = Field(default=None, max_length=cfg.RESOLUTION_NOTE_MAX_LENGTH)
    recorded_by: str = Field(min_length=1, max_length=cfg.RESOLUTION_RECORDED_BY_MAX_LENGTH)

    @model_validator(mode="after")
    def _reject_unknown_outcome_type_early(self):
        # Fast, clear 422 for a typo'd outcome_type before touching the
        # database at all. The 'case must currently be resolved' and
        # 'no duplicate resolution' rules need the database, so those are
        # enforced in app/services/resolution_engine.py.
        if self.outcome_type not in cfg.RESOLUTION_VALID_OUTCOME_TYPES:
            raise ValueError(f"outcome_type must be one of {cfg.RESOLUTION_VALID_OUTCOME_TYPES}, got '{self.outcome_type}'")
        return self


class CaseResolutionOut(BaseModel):
    resolution_id: uuid.UUID
    case_id: uuid.UUID
    outcome_type: str
    resolution_note: str | None
    recorded_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
