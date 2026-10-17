"""
Structured case evidence persistence (Stage 7).

DESIGN DECISION: three separate, fully-normalized tables — one per evidence
type — rather than one table with several nullable reference columns (a
`transaction_id | prediction_id | risk_score_id` row where only one is ever
non-null for a given `evidence_type`). The authorization message explicitly
asked to "avoid unnecessary nullable reference fields if a cleaner
normalized design is possible" — this is that cleaner design: each table
has exactly one, always-required, DB-enforced foreign key to its specific
target, so referential integrity for every evidence type is guaranteed by
PostgreSQL itself, not just application code. app/services/evidence_engine.py
composes reads across all three tables into one unified, chronologically
ordered response.

Each table stores ONLY a reference (a foreign key, plus for risk drivers an
optional index into an already-persisted JSONB array) — never a copy of the
referenced data. No `label`/`chain`/synthetic-role/ground-truth column
exists anywhere in this file, and none of these tables can, by construction,
hold one (they have no free-form JSON column at all).

Evidence is append-only: no `updated_at` on any of these tables, and
app/api/evidence.py implements no update/delete endpoint.
"""
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core import evidence_config as cfg
from app.database import Base


class CaseEvidenceTransaction(Base):
    __tablename__ = "case_evidence_transaction"

    EVIDENCE_TYPE = cfg.EVIDENCE_TYPE_TRANSACTION  # plain class attribute, not a column — used by evidence_engine.py to tag serialized output

    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)

    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("transactions.transaction_id"), nullable=False)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by: Mapped[str] = mapped_column(String(128), nullable=False)  # free-text investigator id; no auth/user table exists in this backend
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CaseEvidenceGraphExplanation(Base):
    __tablename__ = "case_evidence_graph_explanation"

    EVIDENCE_TYPE = cfg.EVIDENCE_TYPE_GRAPH_EXPLANATION

    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)

    # References the specific Stage 3A prediction row whose already-persisted
    # `explanation` JSONB (app/models/prediction.py) is being cited — no
    # second explanation/graph representation is computed or stored here.
    prediction_id: Mapped[int] = mapped_column(Integer, ForeignKey("mule_chain_predictions.id"), nullable=False)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CaseEvidenceRiskDriver(Base):
    __tablename__ = "case_evidence_risk_driver"

    EVIDENCE_TYPE = cfg.EVIDENCE_TYPE_RISK_DRIVER

    evidence_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)

    risk_score_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("risk_scores.score_id"), nullable=False)
    # Optional pointer into the referenced RiskScore's already-persisted
    # `drivers` JSONB array (app/models/risk.py) — e.g. driver_index=0 cites
    # the single strongest driver. NULL means "the risk score as a whole",
    # not "no reference" (risk_score_id above is always required). Bounds
    # (0 <= driver_index < len(drivers)) are validated at write time in
    # evidence_engine.py, since a DB-level CHECK can't reach into another
    # table's JSONB array length.
    driver_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
