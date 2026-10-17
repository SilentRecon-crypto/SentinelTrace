import inspect
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.models.complaint import Complaint  # noqa: E402
from app.services import complaint_graph  # noqa: E402

TEST_COMPLAINT_ID = 452
KNOWN_ROOT_ACCOUNT_ID = 1440
KNOWN_MULE_ACCOUNT_ID = 3722


# ---------------------------------------------------------------
# Graph API
# ---------------------------------------------------------------
def test_graph_valid_complaint(client):
    resp = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert body["complaint_id"] == TEST_COMPLAINT_ID
    assert body["root_account_id"] == KNOWN_ROOT_ACCOUNT_ID
    assert body["max_depth"] == 4
    assert body["node_count"] > 0
    assert body["edge_count"] > 0
    assert body["truncated"] is False


def test_graph_invalid_complaint_returns_404(client):
    resp = client.get("/api/v1/complaints/99999999/graph")
    assert resp.status_code == 404


def test_graph_contains_root_account(client):
    body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph").json()
    root_nodes = [n for n in body["nodes"] if n["is_root"]]
    assert len(root_nodes) == 1
    assert root_nodes[0]["account_id"] == KNOWN_ROOT_ACCOUNT_ID
    assert root_nodes[0]["depth"] == 0
    assert root_nodes[0]["is_candidate"] is False


def test_graph_nodes_are_real_db_accounts(client):
    db = SessionLocal()
    try:
        from app.models.account import Account
        real_ids = {a.account_id for a in db.query(Account).all()}
    finally:
        db.close()
    body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph").json()
    for n in body["nodes"]:
        assert n["account_id"] in real_ids


def test_graph_edges_correspond_to_real_transactions(client):
    db = SessionLocal()
    try:
        from app.models.transaction import Transaction
        real_pairs = {(t.src_account_id, t.dst_account_id) for t in db.query(Transaction).all()}
    finally:
        db.close()
    body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph").json()
    for e in body["edges"]:
        assert (e["src_account_id"], e["dst_account_id"]) in real_pairs
        # every reported transaction_count/total_amount must be backed by
        # actual listed transactions, not a summary invented separately
        assert e["transaction_count"] == len(e["transactions"])
        assert abs(e["total_amount"] - sum(t["amount"] for t in e["transactions"])) < 0.01


def test_graph_depth_bound_respected(client):
    body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph").json()
    for n in body["nodes"]:
        assert 0 <= n["depth"] <= body["max_depth"]


def test_graph_deterministic_serialization(client):
    r1 = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph").json()
    r2 = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph").json()
    assert r1 == r2
    # node/edge ordering itself must be deterministic, not just set-equal
    assert [n["account_id"] for n in r1["nodes"]] == [n["account_id"] for n in r2["nodes"]]
    assert [(e["src_account_id"], e["dst_account_id"]) for e in r1["edges"]] == \
           [(e["src_account_id"], e["dst_account_id"]) for e in r2["edges"]]


# ---------------------------------------------------------------
# Ground-truth isolation in the graph
# ---------------------------------------------------------------
def test_graph_never_exposes_ground_truth_chain(client):
    """Static proof: build_complaint_graph never reads complaint.chain."""
    source = inspect.getsource(complaint_graph.build_complaint_graph)
    assert "complaint.chain" not in source
    assert ".chain" not in source


def test_graph_response_contains_no_ground_truth_fields(client):
    body = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph").json()
    body_str = str(body)
    for forbidden in ('"chain"', '"label"', '"account_type"', "legit_low", "legit_high", '"mule"', "confusor", "adversarial_bait"):
        assert forbidden not in body_str, f"Found forbidden ground-truth term {forbidden!r} in graph response"


def test_graph_does_not_fabricate_prediction_status_without_a_run(client):
    """A complaint that has never had a prediction run must show null
    prediction_rank/model_score on every node, not an invented value."""
    db = SessionLocal()
    try:
        # Pick any complaint with no persisted prediction.
        from app.models.prediction import MuleChainPrediction
        predicted_ids = {p.complaint_id for p in db.query(MuleChainPrediction).all()}
        candidate = db.query(Complaint).filter(~Complaint.complaint_id.in_(predicted_ids)).first()
    finally:
        db.close()
    if candidate is None:
        return  # every complaint has been predicted in this session; nothing to check
    body = client.get(f"/api/v1/complaints/{candidate.complaint_id}/graph").json()
    for n in body["nodes"]:
        assert n["prediction_rank"] is None
        assert n["model_score"] is None


# ---------------------------------------------------------------
# Graph / prediction consistency
# ---------------------------------------------------------------
def test_prediction_candidates_are_represented_in_graph(client):
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    pred = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/mule-chain").json()
    graph = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph").json()

    graph_nodes_by_id = {n["account_id"]: n for n in graph["nodes"]}
    for r in pred["results"]:
        assert r["candidate_account_id"] in graph_nodes_by_id, \
            f"Predicted candidate {r['candidate_account_id']} missing from graph"
        node = graph_nodes_by_id[r["candidate_account_id"]]
        # rank/score in the graph must match the persisted prediction exactly
        assert node["prediction_rank"] == r["rank"]
        assert node["model_score"] == r["model_score"]
        assert node["is_candidate"] is True


def test_known_top_candidate_present_and_consistent(client):
    client.post("/api/v1/predictions/run", json={"complaint_id": TEST_COMPLAINT_ID, "top_k": 5})
    graph = client.get(f"/api/v1/complaints/{TEST_COMPLAINT_ID}/graph").json()
    node = next(n for n in graph["nodes"] if n["account_id"] == KNOWN_MULE_ACCOUNT_ID)
    assert node["prediction_rank"] == 1
    assert node["model_score"] == 0.9969592777671326
    assert node["depth"] == 1
