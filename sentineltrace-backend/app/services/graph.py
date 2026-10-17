"""
Graph engine foundation (Stage 2 infrastructure only).

Builds a directed, time-aware transaction graph from database rows using
NetworkX, and provides basic traversal primitives (neighbors, bounded BFS,
hop distance). This is deliberately a thin infrastructure layer:

- It is NOT a reimplementation of Model A's candidate discovery. The
  authoritative BFS/candidate-generation logic remains
  research_model_a/experiment2_features.py::build_candidate_table, which
  operates directly on pandas DataFrames and already encodes the exact
  time-window / max-depth / feature-computation behavior Model A was
  trained against.
- This module exists so the API layer has a database-backed graph
  representation to build on in a later stage (e.g. for visualization or
  ad-hoc traversal queries), without yet wiring Model A inference through it.
"""
from dataclasses import dataclass

import networkx as nx
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


@dataclass
class TraversalResult:
    start_account_id: int
    visited_account_ids: list[int]
    hop_distances: dict[int, int]
    max_depth_reached: int
    edges_traversed: int


def build_transaction_graph(db: Session, max_day: int | None = None) -> nx.DiGraph:
    """Construct a directed multigraph-free graph (parallel edges collapsed,
    edge attrs hold the list of individual transactions) from the
    `transactions` table. Optionally bounded to day <= max_day."""
    query = db.query(Transaction)
    if max_day is not None:
        query = query.filter(Transaction.day <= max_day)

    graph = nx.DiGraph()
    for tx in query.yield_per(1000):
        if not graph.has_edge(tx.src_account_id, tx.dst_account_id):
            graph.add_edge(tx.src_account_id, tx.dst_account_id, transactions=[])
        graph[tx.src_account_id][tx.dst_account_id]["transactions"].append(
            {"transaction_id": tx.transaction_id, "day": tx.day, "hour": tx.hour, "amount": tx.amount}
        )
    return graph


def get_neighbors(graph: nx.DiGraph, account_id: int) -> list[int]:
    """Outgoing neighbors (accounts this account sent money to)."""
    if account_id not in graph:
        return []
    return list(graph.successors(account_id))


def bounded_bfs(graph: nx.DiGraph, start_account_id: int, max_depth: int = 4) -> TraversalResult:
    """Forward BFS from start_account_id, bounded by max_depth hops.
    Returns every account reachable within that many hops and its hop
    distance from the start account."""
    if start_account_id not in graph:
        return TraversalResult(start_account_id, [], {}, 0, 0)

    hop_distances: dict[int, int] = {start_account_id: 0}
    frontier = [start_account_id]
    edges_traversed = 0
    depth = 0

    while frontier and depth < max_depth:
        next_frontier: list[int] = []
        for node in frontier:
            for neighbor in graph.successors(node):
                edges_traversed += 1
                if neighbor not in hop_distances:
                    hop_distances[neighbor] = depth + 1
                    next_frontier.append(neighbor)
        frontier = next_frontier
        depth += 1

    visited = list(hop_distances.keys())
    max_depth_reached = max(hop_distances.values()) if hop_distances else 0

    return TraversalResult(
        start_account_id=start_account_id,
        visited_account_ids=visited,
        hop_distances=hop_distances,
        max_depth_reached=max_depth_reached,
        edges_traversed=edges_traversed,
    )


def hop_distance(graph: nx.DiGraph, start_account_id: int, target_account_id: int, max_depth: int = 4) -> int | None:
    """Shortest forward hop distance from start to target, bounded by
    max_depth. Returns None if unreachable within that bound."""
    result = bounded_bfs(graph, start_account_id, max_depth=max_depth)
    return result.hop_distances.get(target_account_id)
