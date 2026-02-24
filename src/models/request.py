"""Chat request model with validation."""

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from src.config import get_settings


class ChatRequest(BaseModel):
    """Incoming chat request from user.

    Attributes:
        message: User's text input (required, max 8000 chars)
        model: OpenAI model identifier (optional, defaults to config)
        max_tokens: Maximum tokens in response (optional, range 1-4000)
        user_id: User identifier for memory scoping (optional, defaults to 'anonymous')
        conversation_id: Existing conversation ID to continue (optional)
    """

    message: str = Field(default="", max_length=8000)
    model: Optional[str] = None
    max_tokens: int = Field(default=2000, ge=1, le=4000)
    user_id: str = Field(default="anonymous", max_length=255)
    conversation_id: Optional[str] = Field(default=None, max_length=36)

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        """Strip whitespace from message. Empty string triggers auto-greeting."""
        return v.strip()

    @field_validator("model")
    @classmethod
    def model_allowed(cls, v: Optional[str]) -> Optional[str]:
        """Validate model is in the allowed list."""
        if v is None:
            return v

        settings = get_settings()
        allowed = settings.allowed_models_list
        if v not in allowed:
            raise ValueError(f"Model must be one of {allowed}")
        return v

    @field_validator("conversation_id")
    @classmethod
    def conversation_id_valid_uuid(cls, v: Optional[str]) -> Optional[str]:
        """Validate conversation_id is a valid UUID format if provided."""
        if v is None:
            return v

        # Basic UUID format validation
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        if not uuid_pattern.match(v):
            raise ValueError("conversation_id must be a valid UUID")
        return v

    def get_model(self) -> str:
        """Get model to use, falling back to config default."""
        if self.model:
            return self.model
        return get_settings().openai_model

    def get_max_tokens(self) -> int:
        """Get max tokens, falling back to config default."""
        return self.max_tokens or get_settings().max_tokens
