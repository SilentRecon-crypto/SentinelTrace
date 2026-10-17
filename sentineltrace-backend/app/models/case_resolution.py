"""
Case resolution persistence (Stage 8).

One immutable outcome record per case. No JSON/blob/snapshot column, no
duplicated transaction/prediction/graph/risk/complaint/dataset data — this
table stores only a foreign key to the case, a closed-set outcome value, an
optional free-text note, and who recorded it. See
app/core/resolution_config.py for the full leakage-distinction note
(investigator-recorded outcome vs. synthetic ground-truth labels).

No `label`/`chain`/`acc_type`/synthetic-role column exists here, and none
can be added without also adding a new column (there is no free-form JSON
field to smuggle one into).
"""
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CaseResolution(Base):
    __tablename__ = "case_resolutions"

    resolution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # UNIQUE (not just indexed) — exactly one resolution per case, enforced
    # at the database level, not just in application code.
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    outcome_type: Mapped[str] = mapped_column(String(32), nullable=False)  # closed set, see app.core.resolution_config
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[str] = mapped_column(String(128), nullable=False)  # free-text investigator id; no auth/user table exists in this backend

    # Immutable: no updated_at, no edit/delete endpoint.
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
