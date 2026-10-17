"""
Complaint-specific graph builder (Stage 3B).

DESIGN DECISION (inspected before writing any code): app/services/graph.py's
existing `bounded_bfs` is a generic, TIME-UNAWARE hop-count BFS — it ignores
transaction day ordering entirely. The validated Model A candidate-generation
algorithm in research_model_a/experiment2_features.py is time-aware (forward
tracing only, bounded to a specific day window relative to the complaint).
Using the naive graph.py BFS here would silently produce a different, larger,
and less correct node set than what Model A actually considered — breaking
graph/prediction consistency (Stage 3B section 22) and effectively inventing
a second, competing "similar" traversal algorithm, which the task explicitly
forbids.

Instead, this module builds the complaint graph by REUSING
app.services.candidate_generation.build_candidates_for_complaint() —
the same, already-validated (Stage 3A parity-tested) time-aware BFS — as the
sole source of node membership and hop distance. This guarantees, by
construction, that every graph node (other than the root) is exactly a
Model A candidate for this complaint, with no separate algorithm to drift
out of sync. app/services/graph.py itself is left completely unmodified —
it remains available as general-purpose infrastructure for other uses.

Edges are then filled in by querying the REAL underlying transactions
between any two nodes in that set, within the same day window
candidate_generation already uses. Parallel transactions between the same
two accounts are represented as ONE aggregated edge carrying the full list
of underlying individual transactions (mirroring graph.py's existing
NetworkX edge convention) — no transaction-level detail is lost.

GROUND-TRUTH LEAKAGE FOUND AND FIXED DURING THIS STAGE: `accounts.acc_type`
is NOT real account metadata (e.g. "savings"/"current") — inspecting
research_model_a/generate_graph_v1.py confirms its values
(legit_low/legit_high/hub/confusor/mule/adversarial_bait) are the synthetic
simulation's GROUND-TRUTH role labels, i.e. exactly what Model A is trying
to predict. An earlier draft of this endpoint returned this field directly
as "account_type", which would have let any API consumer bypass the model
entirely by filtering account_type=="mule". It has been deliberately
REMOVED from GraphNode/the API response. Only `created_day` (used
legitimately elsewhere as account_age_days input) is exposed.
"""
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.complaint import Complaint
from app.models.prediction import MuleChainPrediction
from app.models.transaction import Transaction
from app.services.candidate_generation import (
    HISTORICAL_WINDOW_DAYS,
    MAX_DAYS,
    MAX_DEPTH,
    NoCandidatesError,
    build_candidates_for_complaint,
)

# Safety valve only — not expected to trigger on the canonical dataset (the
# largest observed candidate set across the canonical complaints is well
# under 100). Present so a pathological future dataset can't return an
# unbounded response; if hit, `truncated=true` is reported rather than
# silently returning a partial graph as if it were complete.
MAX_GRAPH_NODES = 2000


@dataclass
class GraphNode:
    account_id: int
    created_day: int
    depth: int
    is_root: bool
    is_candidate: bool
    prediction_rank: int | None = None
    model_score: float | None = None


@dataclass
class GraphEdgeTransaction:
    transaction_id: int
    day: int
    hour: int
    amount: float


@dataclass
class GraphEdge:
    src_account_id: int
    dst_account_id: int
    transaction_count: int
    total_amount: float
    first_day: int
    last_day: int
    transactions: list[GraphEdgeTransaction] = field(default_factory=list)


@dataclass
class ComplaintGraph:
    complaint_id: int
    root_account_id: int
    max_depth: int
    node_count: int
    edge_count: int
    truncated: bool
    nodes: list[GraphNode]
    edges: list[GraphEdge]


def build_complaint_graph(db: Session, complaint: Complaint) -> ComplaintGraph:
    root_account_id = complaint.victim

    # 1. Node membership + hop distance: reuse the validated, leakage-safe,
    # time-aware candidate generation unchanged. (May raise NoCandidatesError
    # if the victim has no reachable accounts at all — caller handles this.)
    try:
        feat = build_candidates_for_complaint(db, complaint)
        candidate_ids_with_depth = {int(row.candidate_id): int(row.hop_distance) for row in feat.itertuples()}
    except NoCandidatesError:
        candidate_ids_with_depth = {}

    node_ids = {root_account_id} | set(candidate_ids_with_depth.keys())
    truncated = False
    if len(node_ids) > MAX_GRAPH_NODES:
        # Keep the root plus the MAX_GRAPH_NODES-1 lowest-hop-distance candidates,
        # deterministically (ties broken by account_id), rather than an
        # arbitrary/unordered cut.
        ranked = sorted(candidate_ids_with_depth.items(), key=lambda kv: (kv[1], kv[0]))
        keep = {aid for aid, _ in ranked[: MAX_GRAPH_NODES - 1]}
        node_ids = {root_account_id} | keep
        truncated = True

    # 2. Look up real account rows for every node (real DB data only).
    # NOTE: acc_type is intentionally NOT selected here — see module
    # docstring's GROUND-TRUTH LEAKAGE note.
    account_rows = db.execute(
        select(Account.account_id, Account.created_day).where(Account.account_id.in_(node_ids))
    ).all()
    accounts_by_id = {r.account_id: r for r in account_rows}

    # 3. Attach persisted prediction metadata ONLY (never fabricated, never
    # ground truth). If no prediction has been run yet, these stay None.
    pred_rows = db.execute(
        select(MuleChainPrediction).where(MuleChainPrediction.complaint_id == complaint.complaint_id)
    ).scalars().all()
    pred_by_account = {p.candidate_account_id: p for p in pred_rows}

    nodes = []
    for account_id in sorted(node_ids):  # deterministic order
        acc = accounts_by_id.get(account_id)
        pred = pred_by_account.get(account_id)
        nodes.append(
            GraphNode(
                account_id=account_id,
                created_day=acc.created_day if acc else -1,
                depth=0 if account_id == root_account_id else candidate_ids_with_depth.get(account_id, -1),
                is_root=(account_id == root_account_id),
                is_candidate=(account_id != root_account_id),
                prediction_rank=pred.rank if pred else None,
                model_score=pred.model_score if pred else None,
            )
        )

    # 4. Real transaction edges between nodes in this set, within the same
    # day window candidate_generation itself uses (nothing outside this
    # window could have contributed to the candidate BFS anyway).
    lo = complaint.day - HISTORICAL_WINDOW_DAYS
    hi = complaint.day + MAX_DAYS
    tx_rows = db.execute(
        select(Transaction)
        .where(
            Transaction.src_account_id.in_(node_ids),
            Transaction.dst_account_id.in_(node_ids),
            Transaction.day >= lo,
            Transaction.day <= hi,
        )
        .order_by(Transaction.src_account_id, Transaction.dst_account_id, Transaction.day, Transaction.hour, Transaction.transaction_id)
    ).scalars().all()

    edges_by_pair: dict[tuple[int, int], list[Transaction]] = {}
    for tx in tx_rows:
        edges_by_pair.setdefault((tx.src_account_id, tx.dst_account_id), []).append(tx)

    edges = []
    for (src, dst) in sorted(edges_by_pair.keys()):  # deterministic order
        txs = edges_by_pair[(src, dst)]
        edges.append(
            GraphEdge(
                src_account_id=src,
                dst_account_id=dst,
                transaction_count=len(txs),
                total_amount=round(sum(t.amount for t in txs), 2),
                first_day=min(t.day for t in txs),
                last_day=max(t.day for t in txs),
                transactions=[
                    GraphEdgeTransaction(transaction_id=t.transaction_id, day=t.day, hour=t.hour, amount=t.amount)
                    for t in txs
                ],
            )
        )

    return ComplaintGraph(
        complaint_id=complaint.complaint_id,
        root_account_id=root_account_id,
        max_depth=MAX_DEPTH,
        node_count=len(nodes),
        edge_count=len(edges),
        truncated=truncated,
        nodes=nodes,
        edges=edges,
    )
