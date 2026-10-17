"""
Case + CaseNote persistence (Stage 6).

No `SentinelTrace_Technical_Contract.md` exists in this repository (see
app/core/case_config.py's module docstring). This schema is the smallest
defensible design for "case actions, investigation workflow" as described
— and deliberately deferred — by every prior stage's own scope document.

A Case wraps exactly one Alert (one investigation record per flagged
account/complaint pairing, not per complaint) — mirrors the existing
Integer-FK-with-UUID-own-identity convention used by every other Stage 2+
table (RiskScore.score_id, InterventionWindowRecord.window_id,
Alert.alert_id).

No evidence/attachment table exists here by design — treated as a
separate later concern (see case_config.py). No `label`/`chain`/
synthetic-role/ground-truth column exists here either (Stage 5's own
leakage rules continue to apply: a case never needs, and never stores,
ground truth).
"""
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Case(Base):
    __tablename__ = "cases"

    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # One case per alert. Unique constraint enforces this at the DB level
    # (in addition to the API-level 409-on-duplicate check in case_engine.py).
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.alert_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Denormalized from the parent alert at creation time, purely so case
    # list/queue queries don't need a join for the common case. Never an
    # independent source of truth — always copied from Alert at case-open
    # time, never written to afterward.
    complaint_id: Mapped[int] = mapped_column(Integer, ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False)          # see app.core.case_config
    assigned_to: Mapped[str | None] = mapped_column(String(128), nullable=True)  # free-text investigator id; no auth/user table exists

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CaseNote(Base):
    __tablename__ = "case_notes"

    note_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)

    author: Mapped[str] = mapped_column(String(128), nullable=False)  # free-text investigator id; no auth/user table exists
    note_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Notes are append-only: no updated_at, no edit/delete endpoint.
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
