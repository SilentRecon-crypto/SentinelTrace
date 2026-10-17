from pydantic import BaseModel, ConfigDict


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    complaint_id: int
    victim: int
    day: int
    fraud_amount: float
    n_hops: int
    chain: list[int]
    used_shared_pool: bool
    mode: str
    missing_hop_idx: int


class ComplaintListResponse(BaseModel):
    items: list[ComplaintOut]
    total: int
    limit: int
    offset: int
