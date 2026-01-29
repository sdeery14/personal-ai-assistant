"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4"
    max_tokens: int = 2000
    allowed_models: str = "gpt-4,gpt-4-turbo-preview,gpt-3.5-turbo"

    # Request Handling
    timeout_seconds: int = 30

    # Logging
    log_level: str = "INFO"

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
