"""Configuration settings for the Sales Signal Agent."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Keys
    anthropic_api_key: str
    tavily_api_key: str

    # Timeouts
    request_timeout: int = 30

    # Limits
    max_evidence_per_adapter: int = 10

    # LLM Settings
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 1024

    # Signal Detection Settings
    exec_movement_recency_days: int = 90
    regulatory_deadline_days: int = 180
    job_openings_recency_days: int = 30
    tech_changes_recency_days: int = 90
    budget_trends_recency_days: int = 180

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
