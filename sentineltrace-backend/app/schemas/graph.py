from pydantic import BaseModel


class GraphNodeOut(BaseModel):
    account_id: int
    created_day: int
    depth: int
    is_root: bool
    is_candidate: bool
    prediction_rank: int | None = None
    model_score: float | None = None


class GraphEdgeTransactionOut(BaseModel):
    transaction_id: int
    day: int
    hour: int
    amount: float


class GraphEdgeOut(BaseModel):
    src_account_id: int
    dst_account_id: int
    transaction_count: int
    total_amount: float
    first_day: int
    last_day: int
    transactions: list[GraphEdgeTransactionOut]


class ComplaintGraphResponse(BaseModel):
    complaint_id: int
    root_account_id: int
    max_depth: int
    node_count: int
    edge_count: int
    truncated: bool
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
