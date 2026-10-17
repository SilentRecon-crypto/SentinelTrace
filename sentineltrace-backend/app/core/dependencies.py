"""
Shared FastAPI dependencies, re-exported from one place for convenience.
"""
from app.database import get_db
from app.services.model_a import ModelALoadError, ModelARegistry, get_model_a

__all__ = ["get_db", "get_model_a", "ModelARegistry", "ModelALoadError"]
