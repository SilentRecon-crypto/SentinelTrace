"""
Application configuration.

All values are read from environment variables (see .env.example). No
credentials or secrets are hard-coded here. This module never touches the
frontend's .env.local — it defines an entirely separate configuration
surface for the backend process.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/sentineltrace"

    model_a_path: str = str(BACKEND_ROOT / "artifacts" / "model_a" / "model_a_v1.pkl")
    model_a_feature_metadata_path: str = str(BACKEND_ROOT / "artifacts" / "model_a" / "feature_metadata.json")
    model_a_training_metadata_path: str = str(BACKEND_ROOT / "artifacts" / "model_a" / "training_metadata.json")
    model_a_version: str = "model_a_v1"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Comma-separated list in the environment, e.g. "http://localhost:5173,http://localhost:4173"
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


settings = Settings()
