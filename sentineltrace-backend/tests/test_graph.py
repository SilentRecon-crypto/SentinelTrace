import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.services.graph import bounded_bfs, build_transaction_graph, get_neighbors  # noqa: E402


def test_build_graph_from_real_transactions(client):
    db = SessionLocal()
    try:
        graph = build_transaction_graph(db)
        assert graph.number_of_nodes() > 0
        assert graph.number_of_edges() > 0
    finally:
        db.close()


def test_bounded_bfs_on_real_data(client):
    db = SessionLocal()
    try:
        graph = build_transaction_graph(db)
        # Pick a node that actually has outgoing edges.
        start = next(n for n in graph.nodes if graph.out_degree(n) > 0)
        result = bounded_bfs(graph, start, max_depth=4)
        assert result.start_account_id == start
        assert start in result.visited_account_ids
        assert result.hop_distances[start] == 0
        assert result.max_depth_reached <= 4
        # Every directly-reachable neighbor must be at hop distance 1.
        for neighbor in get_neighbors(graph, start):
            assert result.hop_distances[neighbor] == 1
    finally:
        db.close()


def test_bfs_on_unknown_account_returns_empty(client):
    db = SessionLocal()
    try:
        graph = build_transaction_graph(db)
        result = bounded_bfs(graph, start_account_id=-1, max_depth=4)
        assert result.visited_account_ids == []
    finally:
        db.close()
