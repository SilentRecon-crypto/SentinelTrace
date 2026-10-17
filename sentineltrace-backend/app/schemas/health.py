from pydantic import BaseModel


class HealthResponse(BaseModel):
    api_status: str
    database_connected: bool
    model_a_loaded: bool
    model_a_version: str | None = None
    environment: str
