"""
Mule-chain prediction persistence.

IDEMPOTENCY STRATEGY (chosen and documented per Stage 3A section 13):
"replace current" — each POST /api/v1/predictions/run for a given
complaint_id first deletes any existing rows for that complaint_id, then
inserts a fresh set of ranked rows tagged with a new `prediction_run_id`
(UUID) and `created_at` timestamp. This backend does not yet keep historical
prediction runs; GET /api/v1/complaints/{id}/mule-chain always returns the
single current run. A full audit trail (keeping every past run) is a
reasonable future enhancement but is explicitly out of scope for Stage 3A.

GROUND-TRUTH ISOLATION: this table has NO `label` or `chain` column. Only
the model's own output (`model_score`) and the input features actually used
for scoring are stored.
"""
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MuleChainPrediction(Base):
    __tablename__ = "mule_chain_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True, default=uuid.uuid4)

    complaint_id: Mapped[int] = mapped_column(Integer, ForeignKey("complaints.complaint_id"), nullable=False, index=True)
    candidate_account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.account_id"), nullable=False)

    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    model_score: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    hop_distance: Mapped[int] = mapped_column(Integer, nullable=False)

    # Total candidates discovered by this run (before truncation to top_k).
    # Denormalized onto every row of the run so GET can report it without a
    # separate "prediction_runs" summary table.
    total_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # The exact 8 Model A feature values used for this prediction, keyed by
    # feature name (feature_metadata.json's feature_names_ordered) — stored
    # for reproducibility/audit. Deliberately does NOT include label or chain.
    features: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Deterministic, feature-value-derived observations (see
    # app/services/mule_chain_prediction.py::explain_candidate). Not a causal
    # claim, not SHAP — plain human-readable notes.
    explanation: Mapped[list] = mapped_column(JSONB, nullable=False)

    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
