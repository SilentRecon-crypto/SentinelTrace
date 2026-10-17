"""
RiskScore persistence.

Column names/types follow SentinelTrace_Technical_Contract.md §5's frozen
`risk_scores` table definition as closely as possible. ONE deliberate
adaptation, consistent with every table since Stage 2/3A/3B: `complaint_id`
and `account_id` are INTEGER foreign keys matching this project's actual
accounts/complaints primary keys (the synthetic generator's native IDs),
not UUID as the Contract's generic schema assumes — the Contract was
written assuming a UUID-keyed schema throughout; this project's real,
already-built tables use integer PKs from Stage 1's synthetic data, and
changing that now would break every existing table/endpoint. `score_id`
itself IS a UUID (its own identity, consistent with Stage 3B's
`prediction_run_id` convention).

No `label`/`chain`/ground-truth column exists here by design.
"""
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RiskScore(Base):
    __tablename__ = "risk_scores"

    score_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    complaint_id: Mapped[int] = mapped_column(Integer, ForeignKey("complaints.complaint_id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=False)

    ml_score: Mapped[float] = mapped_column(Float, nullable=False)          # Contract §8, copied verbatim from MuleChainPrediction
    heuristic_score: Mapped[float] = mapped_column(Float, nullable=False)   # Graph flow-decay formula, Contract §10

    priority_level: Mapped[str] = mapped_column(String(16), nullable=False)   # low|medium|high|critical
    priority_value: Mapped[float] = mapped_column(Float, nullable=False)
    priority_method: Mapped[str] = mapped_column(String(32), nullable=False)  # always "heuristic_combination"

    drivers: Mapped[list] = mapped_column(JSONB, nullable=False)  # array of {factor, contribution, description}

    generated_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
