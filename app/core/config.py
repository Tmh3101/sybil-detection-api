from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Note: We intentionally do not instantiate `Settings()` at import-time to
    keep `uvicorn app.main:app` runnable without requiring env vars yet.
    """

    MODAL_TOKEN_ID: str
    MODAL_TOKEN_SECRET: str

    MODAL_APP_NAME: str = "sybil-discovery-engine"
    MODAL_DISCOVERY_FUNCTION: str = "train_gae_pipeline"

    GRAPH_DATA_PATH: str = "data/graph.pt"
    NODE_METADATA_PATH: str = "data/nodes_full.csv"

    # Kept here for consistency with template-style routing.
    API_V1_STR: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

