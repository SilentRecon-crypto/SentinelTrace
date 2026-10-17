"""
InterventionWindow persistence.

Column names/types follow SentinelTrace_Technical_Contract.md §5's frozen
`intervention_windows` table definition, with the same Integer-FK
adaptation documented in app/models/risk.py. `validation_status` defaults
to the Contract's fixed literal "synthetic_demo_only" and this backend
never writes any other value into it.
"""
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InterventionWindowRecord(Base):
    __tablename__ = "intervention_windows"

    window_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    complaint_id: Mapped[int] = mapped_column(Integer, ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=False)

    # NOTE: Contract §5 names this column `current_time`, which is a reserved
    # word in PostgreSQL (a builtin date/time function). To avoid relying on
    # SQLAlchemy's automatic identifier quoting for a reserved word, this
    # column is created as `request_time` with the same meaning/semantics;
    # the API response still uses the Contract's exact field name
    # `current_time` (see app/schemas/intervention.py).
    request_time: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_cashout_time: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_window_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="synthetic_demo_only")
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    generated_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
