"""
Alert persistence (Stage 5).

No `SentinelTrace_Technical_Contract.md` file exists in this repository
(verified by exhaustive search before Stage 5 work began — see
app/core/alert_config.py's module docstring for detail), so this schema is
the "smallest defensible alert model" called for by the Stage 5 brief §5,
built from concepts equivalent to the ones it lists, and following the
exact same Integer-FK-with-UUID-own-identity convention already used by
RiskScore (score_id) and InterventionWindowRecord (window_id) in
app/models/risk.py / app/models/intervention.py.

No `label`/`chain`/synthetic-role/ground-truth column exists here by
design (Stage 5 brief §5, §15).
"""
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    complaint_id: Mapped[int] = mapped_column(Integer, ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=False)

    # Traceability back to the exact Stage 4 risk row this alert was derived
    # from (Stage 5 brief §5: "prediction/risk relationship if appropriate").
    risk_score_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("risk_scores.score_id", ondelete="CASCADE"), nullable=False, index=True)

    # Model A candidate rank for this account, copied verbatim from the
    # existing MuleChainPrediction row — used only as a deterministic
    # ordering tie-breaker (§13), never recomputed.
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)      # see app.core.alert_config
    severity: Mapped[str] = mapped_column(String(16), nullable=False)        # copied verbatim from RiskScore.priority_level
    status: Mapped[str] = mapped_column(String(16), nullable=False)          # open|acknowledged|resolved

    # Stage 5's OWN prioritization value — distinct from ml_score and from
    # Stage 4's priority_value (also stored below, verbatim, for transparent
    # ordering/display — never overwritten or reinterpreted as anything else).
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_priority_value: Mapped[float] = mapped_column(Float, nullable=False)  # Stage 4 priority.value, copied verbatim

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    model_version: Mapped[str] = mapped_column(String(64), nullable=False)   # Model A version, for traceability only

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
