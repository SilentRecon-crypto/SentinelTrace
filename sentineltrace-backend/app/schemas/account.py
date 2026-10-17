from pydantic import BaseModel, ConfigDict


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    acc_type: str
    created_day: int


class AccountListResponse(BaseModel):
    items: list[AccountOut]
    total: int
    limit: int
    offset: int
