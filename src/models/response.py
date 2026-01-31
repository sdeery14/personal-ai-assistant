"""Chat response models for streaming and completion."""

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class StreamChunk(BaseModel):
    """Individual piece of streamed response (SSE event).

    Attributes:
        content: Text fragment from LLM
        sequence: Zero-indexed chunk number
        is_final: True if this is the last chunk
        correlation_id: Request tracking ID (UUID4)
        error_type: Optional error type for retraction chunks (e.g., "output_guardrail_violation")
        message: Optional user-facing message for retraction chunks
        redacted_length: Optional length of content that was redacted/retracted
    """

    content: str
    sequence: int = Field(ge=0)
    is_final: bool = False
    correlation_id: UUID
    error_type: Optional[str] = None
    message: Optional[str] = None
    redacted_length: Optional[int] = None


class ChatResponse(BaseModel):
    """Metadata about completed response (logged, not streamed).

    Attributes:
        correlation_id: Matches request tracking ID
        status: success, error, or timeout
        total_tokens: Prompt + completion tokens (if available)
        duration_ms: Request processing time in milliseconds
        model_used: Actual model that processed request
        error_message: Present only if status is error
    """

    correlation_id: UUID
    status: Literal["success", "error", "timeout"]
    total_tokens: Optional[int] = None
    duration_ms: int = Field(ge=0)
    model_used: str
    error_message: Optional[str] = None

    @model_validator(mode="after")
    def error_message_required_if_error(self) -> "ChatResponse":
        """Require error_message when status is error."""
        if self.status == "error" and not self.error_message:
            raise ValueError("error_message required when status is error")
        return self


class ErrorResponse(BaseModel):
    """Error response following constitutional UX pattern.

    Three-part format: what happened + why + what to do
    """

    error: str  # What happened
    detail: str  # Why and what to do
    correlation_id: UUID


class GuardrailErrorResponse(BaseModel):
    """Error response for guardrail violations.

    Attributes:
        error: High-level error type (e.g., "guardrail_violation")
        message: User-safe explanation (no technical details)
        correlation_id: Request tracking ID for debugging
        guardrail_type: "input" or "output"
        error_type: Specific error code (e.g., "input_guardrail_violation")
    """

    error: str
    message: str
    correlation_id: UUID
    guardrail_type: str
    error_type: str
