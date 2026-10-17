"""
Model A mule-chain inference orchestration.

Pipeline:
    complaint (PostgreSQL)
        -> candidate discovery + feature engineering (app.services.candidate_generation,
           which calls the unmodified research_model_a.experiment2_features.build_candidate_table)
        -> scoring (the already-loaded model_a_v1.pkl, via app.services.model_a.ModelARegistry)
        -> ranking (descending model_score, deterministic tie-break on candidate_account_id)
        -> persistence (app.models.prediction.MuleChainPrediction, "replace current" strategy)
        -> API response

GROUND-TRUTH ISOLATION: this module never reads `label` or `chain` for
scoring or ranking. The `label` column returned by build_candidate_table()
is dropped immediately after candidate generation and never touches the
model, the response, or the database.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models.complaint import Complaint
from app.models.prediction import MuleChainPrediction
from app.services.candidate_generation import NoCandidatesError, build_candidates_for_complaint
from app.services.model_a import ModelARegistry

MIN_TOP_K = 1
MAX_TOP_K = 50
DEFAULT_TOP_K = 5


class ComplaintNotFoundError(RuntimeError):
    pass


class InvalidTopKError(RuntimeError):
    pass


@dataclass
class RankedCandidate:
    rank: int
    candidate_account_id: int
    model_score: float
    hop_distance: int
    features: dict[str, float]
    explanation: list[str] = field(default_factory=list)


@dataclass
class PredictionResult:
    complaint_id: int
    model_version: str
    generated_at: datetime
    candidate_count: int
    results: list[RankedCandidate]
    prediction_run_id: uuid.UUID


def explain_candidate(features: dict[str, float]) -> list[str]:
    """Deterministic, feature-value-derived observations. Not a causal
    attribution method (no SHAP/permutation importance here) — plain
    threshold-based notes on the actual computed feature values for this
    candidate, so an analyst has something more legible than a bare score."""
    notes = []
    if features["hop_distance"] <= 1:
        notes.append("Directly reachable within 1 hop of the victim account")
    if features["pass_through_ratio"] >= 0.7:
        notes.append(f"High pass-through ratio ({features['pass_through_ratio']:.2f}) — funds moved on quickly")
    if features["fan_in_recent_30d"] >= 3:
        notes.append(f"Elevated recent fan-in ({int(features['fan_in_recent_30d'])} distinct senders in 30 days)")
    if features["subgraph_degree_centrality"] >= 0.8:
        notes.append(f"High structural centrality within this complaint's candidate network ({features['subgraph_degree_centrality']:.2f} percentile)")
    if features["account_age_days"] <= 7:
        notes.append(f"Very new account ({int(features['account_age_days'])} days old at time of complaint)")
    if features["amount_consistency"] >= 0.8:
        notes.append(f"Traced-in amount is consistent with the reported fraud amount (ratio {features['amount_consistency']:.2f})")
    if not notes:
        notes.append("No individually notable signals; ranked primarily on the combined model score")
    return notes


def run_prediction(db: Session, model: ModelARegistry, complaint_id: int, top_k: int = DEFAULT_TOP_K) -> PredictionResult:
    if not (MIN_TOP_K <= top_k <= MAX_TOP_K):
        raise InvalidTopKError(f"top_k must be between {MIN_TOP_K} and {MAX_TOP_K}, got {top_k}")

    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise ComplaintNotFoundError(f"Complaint {complaint_id} not found")

    # 1. Candidate discovery + feature engineering (unmodified research logic).
    feat = build_candidates_for_complaint(db, complaint)  # raises NoCandidatesError if empty

    # 2. GROUND-TRUTH ISOLATION: drop label/leakage-adjacent columns immediately,
    # before scoring, so they cannot influence anything downstream.
    assert "label" in feat.columns  # sanity: confirms we know exactly what we're dropping
    feat = feat.drop(columns=["label"])

    # 3. Scoring — batch call against the already-loaded model.
    scores = model.predict_proba_batch(feat)
    feat = feat.assign(model_score=scores)

    # 4. Deterministic ranking: score desc, tie-break candidate_id asc.
    feat = feat.sort_values(by=["model_score", "candidate_id"], ascending=[False, True]).reset_index(drop=True)
    feat.insert(0, "rank", feat.index + 1)

    candidate_count = len(feat)
    top = feat.head(top_k)

    results = []
    for _, row in top.iterrows():
        feature_values = {f: float(row[f]) for f in model.feature_names_ordered}
        results.append(
            RankedCandidate(
                rank=int(row["rank"]),
                candidate_account_id=int(row["candidate_id"]),
                model_score=float(row["model_score"]),
                hop_distance=int(row["hop_distance"]),
                features=feature_values,
                explanation=explain_candidate(feature_values),
            )
        )

    prediction_run_id = uuid.uuid4()

    # 5. Persistence — "replace current" strategy (see app/models/prediction.py
    # docstring), made ATOMIC and CONCURRENCY-SAFE:
    #
    # ATOMICITY: delete + insert are wrapped in an explicit try/except that
    # rolls back on any failure, so a partial write (e.g. old rows deleted
    # but new rows not yet inserted) can never be left committed. SQLAlchemy
    # would also roll back an uncommitted transaction when the session is
    # closed, but we make this explicit and directly testable rather than
    # relying on that implicit behavior.
    #
    # CONCURRENCY: two simultaneous POST /predictions/run calls for the SAME
    # complaint_id could otherwise interleave their delete+insert and leave
    # an inconsistent mix of rows from two different runs. We take a
    # PostgreSQL transaction-scoped advisory lock keyed on complaint_id
    # (pg_advisory_xact_lock) before the delete. This serializes concurrent
    # writers for the SAME complaint (the second request simply waits for
    # the first transaction to commit or roll back) while never blocking
    # concurrent requests for DIFFERENT complaints. The lock is released
    # automatically at commit/rollback — no manual unlock needed, and no
    # risk of a leaked lock if the process crashes mid-request.
    try:
        db.execute(text("SELECT pg_advisory_xact_lock(:complaint_id)"), {"complaint_id": complaint_id})
        db.execute(delete(MuleChainPrediction).where(MuleChainPrediction.complaint_id == complaint_id))
        persisted_rows = []
        for r in results:
            row = MuleChainPrediction(
                prediction_run_id=prediction_run_id,
                complaint_id=complaint_id,
                candidate_account_id=r.candidate_account_id,
                rank=r.rank,
                model_score=r.model_score,
                model_version=model.version,
                hop_distance=r.hop_distance,
                total_candidate_count=candidate_count,
                features=r.features,
                explanation=r.explanation,
            )
            db.add(row)
            persisted_rows.append(row)
        db.commit()
        # Read back the DB-assigned timestamp so POST and GET report the
        # exact same generated_at for the exact same run (previously POST
        # returned a pre-commit Python timestamp, which could differ from
        # the server-generated `created_at` by tens of milliseconds).
        db.refresh(persisted_rows[0])
        generated_at = persisted_rows[0].created_at
    except Exception:
        db.rollback()
        raise

    return PredictionResult(
        complaint_id=complaint_id,
        model_version=model.version,
        generated_at=generated_at,
        candidate_count=candidate_count,
        results=results,
        prediction_run_id=prediction_run_id,
    )


def get_latest_prediction(db: Session, complaint_id: int) -> list[MuleChainPrediction] | None:
    rows = db.execute(
        select(MuleChainPrediction)
        .where(MuleChainPrediction.complaint_id == complaint_id)
        .order_by(MuleChainPrediction.rank)
    ).scalars().all()
    return list(rows) if rows else None
