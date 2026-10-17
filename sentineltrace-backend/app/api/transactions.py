from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionListResponse, TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    account_id: int | None = Query(None, description="Filter to transactions involving this account (either side)"),
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    query = db.query(Transaction)
    if account_id is not None:
        query = query.filter(
            (Transaction.src_account_id == account_id) | (Transaction.dst_account_id == account_id)
        )
    total = query.count()
    rows = query.order_by(Transaction.transaction_id).offset(offset).limit(limit).all()
    return TransactionListResponse(
        items=[TransactionOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
