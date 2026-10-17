import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Account  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def ensure_seeded():
    """Make sure the schema exists and the canonical Stage 1 data is loaded
    before any test runs, so the test suite is runnable standalone. Uses the
    real seed script against the real dev database configured in .env —
    Stage 2 does not introduce a separate test-database setup."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        count = session.query(Account).count()
    finally:
        session.close()

    if count == 0:
        from scripts.seed_model_a import main as seed_main
        seed_main()


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c
