"""
SentinelTrace backend — Stage 2 foundation.

Now includes Stage 1-5: FastAPI app, PostgreSQL connectivity, Model A
loaded once at startup, account/transaction/complaint retrieval, a
database-backed graph engine, Model A predictions, risk scoring +
intervention windows, and alert generation/prioritization. Deliberately
does NOT implement case actions/investigation workflow, authentication,
authorization, notifications, or Model B — those are later stages.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import accounts, alerts, cases, complaints, dossier, evidence, health, predictions, resolution, risk, transactions
from app.config import settings
from app.services.model_a import ModelALoadError, load_model_a

logger = logging.getLogger("sentineltrace")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load Model A exactly once, at process startup — not per-request.
    try:
        registry = load_model_a()
        logger.info(
            "Model A loaded: version=%s features=%s", registry.version, registry.feature_names_ordered
        )
    except ModelALoadError as exc:
        # Fail loudly rather than silently starting without a model.
        logger.error("Model A failed to load at startup: %s", exc)
        raise
    yield
    # No teardown needed for Stage 2 (no open resources beyond the DB pool,
    # which SQLAlchemy manages on process exit).


app = FastAPI(
    title="SentinelTrace API",
    version="0.2.0",
    description="Stage 2 backend foundation — Model A (mule-chain identification) runtime, database-backed.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(complaints.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(risk.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(alerts.queue_router, prefix="/api/v1")
app.include_router(cases.alerts_router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(evidence.router, prefix="/api/v1")
app.include_router(resolution.router, prefix="/api/v1")
app.include_router(dossier.router, prefix="/api/v1")
