import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.core import evidence_config as cfg


class CaseEvidenceCreateRequest(BaseModel):
    """One flat request shape covering all three evidence types — the field(s)
    that are relevant depend on `evidence_type` (see app/core/evidence_config.py
    and app/services/evidence_engine.py for the exact per-type requirement and
    validation). Providing fields that don't belong to the given evidence_type
    is rejected as a malformed request (422), not silently ignored."""
    evidence_type: str = Field(description=f"One of {cfg.EVIDENCE_VALID_TYPES}")
    transaction_id: int | None = Field(default=None, description=f"Required iff evidence_type == '{cfg.EVIDENCE_TYPE_TRANSACTION}'")
    prediction_id: int | None = Field(default=None, description=f"Required iff evidence_type == '{cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION}'")
    risk_score_id: uuid.UUID | None = Field(default=None, description=f"Required iff evidence_type == '{cfg.EVIDENCE_TYPE_RISK_DRIVER}'")
    driver_index: int | None = Field(default=None, ge=0, description=f"Optional, only meaningful with evidence_type == '{cfg.EVIDENCE_TYPE_RISK_DRIVER}'")
    note: str | None = Field(default=None, max_length=cfg.EVIDENCE_NOTE_MAX_LENGTH)
    added_by: str = Field(min_length=1, max_length=cfg.EVIDENCE_ADDED_BY_MAX_LENGTH)

    @model_validator(mode="after")
    def _reject_unknown_type_early(self):
        # Full per-type field-shape validation happens in evidence_engine.py
        # (it needs the case's account/complaint to fully validate anyway);
        # this just gives a fast, clear 422 for a typo'd evidence_type before
        # touching the database at all.
        if self.evidence_type not in cfg.EVIDENCE_VALID_TYPES:
            raise ValueError(f"evidence_type must be one of {cfg.EVIDENCE_VALID_TYPES}, got '{self.evidence_type}'")
        return self


class CaseEvidenceOut(BaseModel):
    evidence_id: uuid.UUID
    case_id: uuid.UUID
    evidence_type: str
    transaction_id: int | None = None
    prediction_id: int | None = None
    risk_score_id: uuid.UUID | None = None
    driver_index: int | None = None
    note: str | None
    added_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseEvidenceListResponse(BaseModel):
    case_id: uuid.UUID
    results: list[CaseEvidenceOut]
