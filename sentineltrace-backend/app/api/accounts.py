from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.account import Account
from app.schemas.account import AccountListResponse, AccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=AccountListResponse)
def list_accounts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    acc_type: str | None = Query(None, description="Filter by account type, e.g. 'mule'"),
    db: Session = Depends(get_db),
) -> AccountListResponse:
    query = db.query(Account)
    if acc_type:
        query = query.filter(Account.acc_type == acc_type)
    total = query.count()
    rows = query.order_by(Account.account_id).offset(offset).limit(limit).all()
    return AccountListResponse(
        items=[AccountOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)) -> AccountOut:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account {account_id} not found")
    return AccountOut.model_validate(account)
