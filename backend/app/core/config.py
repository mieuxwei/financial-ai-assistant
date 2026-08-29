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
    b5_intelligence_config_path: str = "research/configs/b5_nlp_intelligence_integration.v1.json"
    f11b_service_key_id: str = ""
    f11b_service_secret: str = ""
    f11b_controlled_fixture_path: str = "demo/fixtures/controlled_dashboard_demo.v1.json"
    demo_gas_service_token: str = ""
    demo_universe_config_path: str = "research/configs/risk_market_dataset.v1.json"
    demo_retention_days: int = 30
    demo_max_holdings: int = 5
    demo_max_shares: int = 10_000_000
    demo_max_average_cost: int = 1_000_000
    demo_per_user_requests_per_minute: int = 30
    demo_global_requests_per_minute: int = 300

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
