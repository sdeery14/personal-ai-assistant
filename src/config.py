"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4.1"
    max_tokens: int = 2000
    allowed_models: str = "gpt-4.1,gpt-4,gpt-4-turbo-preview,gpt-3.5-turbo"

    # Request Handling
    timeout_seconds: int = 30

    # Logging
    log_level: str = "INFO"

    # Database (Feature 004)
    postgres_url: str = "postgresql://assistant:assistant_dev_password@localhost:5432/assistant"

    # Redis (Feature 004)
    redis_url: str = "redis://localhost:6379/0"

    # Memory Configuration (Feature 004)
    embedding_model: str = "text-embedding-3-small"
    token_budget: int = 1000  # Max tokens for memory injection
    min_relevance: float = 0.3  # Minimum relevance score threshold
    max_results: int = 10  # Maximum memory items to return
    memory_rate_limit: int = 10  # Queries per minute per user
    embedding_cache_ttl: int = 604800  # 7 days in seconds
    session_ttl: int = 86400  # 24 hours in seconds
    rrf_k: int = 60  # RRF constant (standard value, not configurable)

    # Weather API Configuration (Feature 005)
    openweathermap_api_key: str = ""  # Required for weather tool
    weather_api_base_url: str = "https://api.openweathermap.org/data/2.5"
    weather_cache_ttl_current: int = 600  # 10 minutes for current weather
    weather_cache_ttl_forecast: int = 1800  # 30 minutes for forecast
    weather_api_timeout: int = 5  # 5 second timeout per request

    @property
    def allowed_models_list(self) -> List[str]:
        """Parse comma-separated allowed models into a list."""
        return [m.strip() for m in self.allowed_models.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
