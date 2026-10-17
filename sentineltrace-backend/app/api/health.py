from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_db
from app.schemas.health import HealthResponse
from app.services import model_a

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    loaded = model_a.is_loaded()
    version = None
    if loaded:
        version = model_a.get_model_a().version

    return HealthResponse(
        api_status="ok",
        database_connected=db_connected,
        model_a_loaded=loaded,
        model_a_version=version,
        environment=settings.environment,
    )
