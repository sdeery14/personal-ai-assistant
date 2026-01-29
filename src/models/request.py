"""Chat request model with validation."""

from typing import List

from pydantic import BaseModel, Field, field_validator

from src.config import get_settings


class ChatRequest(BaseModel):
    """Incoming chat request from user.

    Attributes:
        message: User's text input (required, max 8000 chars)
        model: OpenAI model identifier (optional, defaults to config)
        max_tokens: Maximum tokens in response (optional, range 1-4000)
    """

    message: str = Field(..., min_length=1, max_length=8000)
    model: str | None = None
    max_tokens: int = Field(default=2000, ge=1, le=4000)

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        """Ensure message is not empty or whitespace only."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty or whitespace only")
        return stripped

    @field_validator("model")
    @classmethod
    def model_allowed(cls, v: str | None) -> str | None:
        """Validate model is in the allowed list."""
        if v is None:
            return v

        settings = get_settings()
        allowed = settings.allowed_models_list
        if v not in allowed:
            raise ValueError(f"Model must be one of {allowed}")
        return v

    def get_model(self) -> str:
        """Get model to use, falling back to config default."""
        if self.model:
            return self.model
        return get_settings().openai_model

    def get_max_tokens(self) -> int:
        """Get max tokens, falling back to config default."""
        return self.max_tokens or get_settings().max_tokens
