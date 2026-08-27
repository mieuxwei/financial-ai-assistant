from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a local .env file."""

    app_env: Literal["development", "test", "production"] = "development"
    service_name: str = "financial-ai-assistant"
    database_url: str = ""
    line_user_id_pepper: str = ""
    line_channel_access_token: str = ""
    line_channel_secret: str = ""
    gemini_api_key: str = ""
    perplexity_api_key: str = ""
    market_data_provider: str = "yahoo"
    news_provider: str = ""
    final_model_artifact_path: str = ".tools/models/f7-final-ridge-research-v1/model.json"
    backend_integration_config_path: str = "research/configs/backend_integration.v1.json"

    @property
    def resolved_database_url(self) -> str:
        return self.database_url or "sqlite:///./.local/financial_ai.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
