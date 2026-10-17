import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core import case_config as cfg


class CaseNoteOut(BaseModel):
    note_id: uuid.UUID
    case_id: uuid.UUID
    author: str
    note_text: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseOut(BaseModel):
    case_id: uuid.UUID
    alert_id: uuid.UUID
    complaint_id: int
    account_id: int
    status: str
    assigned_to: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaseListResponse(BaseModel):
    results: list[CaseOut]


class CaseNoteListResponse(BaseModel):
    case_id: uuid.UUID
    results: list[CaseNoteOut]


class CaseUpdateRequest(BaseModel):
    """Both fields optional; omit a field entirely to leave it unchanged.
    `assigned_to` may be explicitly set to null to clear the assignment
    (distinct from omitting it) — see app/api/cases.py for how that
    distinction is detected."""
    status: str | None = Field(default=None, description=f"One of {cfg.CASE_VALID_STATUSES}")
    assigned_to: str | None = Field(default=None, max_length=cfg.CASE_ASSIGNED_TO_MAX_LENGTH)


class CaseNoteCreateRequest(BaseModel):
    author: str = Field(min_length=1, max_length=cfg.CASE_ASSIGNED_TO_MAX_LENGTH)
    note_text: str = Field(min_length=1, max_length=cfg.CASE_NOTE_MAX_LENGTH)
