import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.account import Account
from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintListResponse, ComplaintOut
from app.schemas.graph import ComplaintGraphResponse
from app.schemas.prediction import PredictionRunResponse, RankedCandidateOut
from app.services.complaint_graph import build_complaint_graph
from app.services.mule_chain_prediction import get_latest_prediction

logger = logging.getLogger("sentineltrace")

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.get("", response_model=ComplaintListResponse)
def list_complaints(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ComplaintListResponse:
    query = db.query(Complaint)
    total = query.count()
    rows = query.order_by(Complaint.complaint_id).offset(offset).limit(limit).all()
    return ComplaintListResponse(
        items=[ComplaintOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)) -> ComplaintOut:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")
    return ComplaintOut.model_validate(complaint)


@router.get("/{complaint_id}/mule-chain", response_model=PredictionRunResponse)
def get_mule_chain_prediction(complaint_id: int, db: Session = Depends(get_db)) -> PredictionRunResponse:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")

    rows = get_latest_prediction(db, complaint_id)
    if rows is None:
        raise HTTPException(
            status_code=404,
            detail=f"No Model A prediction has been run yet for complaint {complaint_id}. "
                   f"POST /api/v1/predictions/run first.",
        )

    return PredictionRunResponse(
        complaint_id=complaint_id,
        model_version=rows[0].model_version,
        generated_at=rows[0].created_at,
        prediction_run_id=rows[0].prediction_run_id,
        candidate_count=rows[0].total_candidate_count,
        results=[
            RankedCandidateOut(
                rank=r.rank,
                candidate_account_id=r.candidate_account_id,
                model_score=r.model_score,
                hop_distance=r.hop_distance,
                features=r.features,
                explanation=r.explanation,
            )
            for r in rows
        ],
    )


@router.get("/{complaint_id}/graph", response_model=ComplaintGraphResponse)
def get_complaint_graph(complaint_id: int, db: Session = Depends(get_db)) -> ComplaintGraphResponse:
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")

    if db.get(Account, complaint.victim) is None:
        raise HTTPException(status_code=422, detail=f"Complaint {complaint_id}'s victim account {complaint.victim} does not exist in the accounts table")

    try:
        graph = build_complaint_graph(db, complaint)
    except Exception:
        logger.exception("Graph construction failed for complaint_id=%s", complaint_id)
        raise HTTPException(status_code=500, detail="Graph construction failed due to an internal error.") from None

    return ComplaintGraphResponse(
        complaint_id=graph.complaint_id,
        root_account_id=graph.root_account_id,
        max_depth=graph.max_depth,
        node_count=graph.node_count,
        edge_count=graph.edge_count,
        truncated=graph.truncated,
        nodes=[
            {
                "account_id": n.account_id, "created_day": n.created_day,
                "depth": n.depth, "is_root": n.is_root, "is_candidate": n.is_candidate,
                "prediction_rank": n.prediction_rank, "model_score": n.model_score,
            }
            for n in graph.nodes
        ],
        edges=[
            {
                "src_account_id": e.src_account_id, "dst_account_id": e.dst_account_id,
                "transaction_count": e.transaction_count, "total_amount": e.total_amount,
                "first_day": e.first_day, "last_day": e.last_day,
                "transactions": [
                    {"transaction_id": t.transaction_id, "day": t.day, "hour": t.hour, "amount": t.amount}
                    for t in e.transactions
                ],
            }
            for e in graph.edges
        ],
    )
