"""API route definitions for chat and health endpoints."""

import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from agents.exceptions import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
)

from src.api.dependencies import get_current_user
from src.config import get_settings
from src.models.request import ChatRequest
from src.models.response import ErrorResponse, GuardrailErrorResponse, StreamChunk
from src.models.user import User
from src.services.chat_service import ChatService


router = APIRouter()


def get_chat_service() -> ChatService:
    """Get chat service instance (lazy loaded)."""
    return ChatService()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Status and timestamp in ISO8601 format
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Check database health
    try:
        from src.database import health_check as db_health_check
        db_healthy = await db_health_check()
        health_status["database"] = "healthy" if db_healthy else "unhealthy"
    except Exception:
        health_status["database"] = "unavailable"

    # Check Redis health
    try:
        from src.services.redis_service import get_redis
        redis_client = await get_redis()
        health_status["redis"] = "healthy" if redis_client else "unavailable"
    except Exception:
        health_status["redis"] = "unavailable"

    return health_status


async def generate_sse_stream(
    request: ChatRequest,
    correlation_id: str,
) -> AsyncGenerator[str, None]:
    """Generate SSE-formatted stream from chat service.

    Args:
        request: Validated chat request
        correlation_id: Request tracking UUID

    Yields:
        SSE-formatted data strings: "data: {json}\n\n"
    """
    from uuid import UUID

    correlation_uuid = UUID(correlation_id)
    chat_service = get_chat_service()

    async for chunk in chat_service.stream_completion(
        message=request.message,
        correlation_id=correlation_uuid,
        model=request.get_model(),
        max_tokens=request.get_max_tokens(),
        user_id=request.user_id,
        conversation_id=request.conversation_id,
    ):
        chunk_dict = {
            "content": chunk.content,
            "sequence": chunk.sequence,
            "is_final": chunk.is_final,
            "correlation_id": str(chunk.correlation_id),
            "conversation_id": chunk.conversation_id,
        }
        yield f"data: {json.dumps(chunk_dict)}\n\n"


async def generate_sse_stream_with_timeout(
    request: ChatRequest,
    correlation_id: str,
) -> AsyncGenerator[str, None]:
    """Generate SSE stream with timeout handling.

    Wraps the stream generator with asyncio timeout and error handling.
    Logs request lifecycle events (start, completion, errors).
    """
    import time

    settings = get_settings()
    logger = structlog.get_logger()
    start_time = time.perf_counter()
    chunk_count = 0
    status = "success"

    try:
        async with asyncio.timeout(settings.timeout_seconds):
            async for chunk in generate_sse_stream(request, correlation_id):
                chunk_count += 1
                yield chunk
    except asyncio.TimeoutError:
        status = "timeout"
        # Stream timeout error as SSE event
        logger.error(
            "stream_timeout",
            correlation_id=correlation_id,
            timeout_seconds=settings.timeout_seconds,
        )
        error_chunk = {
            "content": "",
            "sequence": -1,
            "is_final": True,
            "correlation_id": correlation_id,
            "error": "Request timed out. The server took too long to respond. Please try again with a shorter message or try again later.",
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
    except (InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered) as e:
        # Guardrail blocked the request or response - stream as SSE error event
        status = "blocked"
        guardrail_type = (
            "input" if isinstance(e, InputGuardrailTripwireTriggered) else "output"
        )

        logger.warning(
            f"{guardrail_type}_guardrail_triggered",
            correlation_id=correlation_id,
            guardrail_type=guardrail_type,
            error_type=type(e).__name__,
        )

        # User-safe message with no technical details
        message = (
            "Your request cannot be processed due to security concerns. Please rephrase your message and try again."
            if guardrail_type == "input"
            else "Previous content retracted due to safety concerns. Please try a different request."
        )

        error_chunk = {
            "content": "",
            "sequence": -1,
            "is_final": True,
            "correlation_id": correlation_id,
            "error": message,
            "error_type": f"{guardrail_type}_guardrail_violation",
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
    except Exception as e:
        status = "error"
        # Stream error as SSE event with user-friendly message
        logger.error(
            "stream_error",
            correlation_id=correlation_id,
            error_type=type(e).__name__,
            error_message=str(e),
        )
        error_chunk = {
            "content": "",
            "sequence": -1,
            "is_final": True,
            "correlation_id": correlation_id,
            "error": f"An error occurred while processing your request. {type(e).__name__}: Please try again.",
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
    finally:
        # Log response completion with lifecycle metrics
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "response_complete",
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            chunk_count=chunk_count,
            status=status,
            user_id=request.user_id,
        )


@router.post("/chat")
async def chat(
    request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Send a message and receive streamed response.

    Accepts a text message and streams back the LLM's response in real-time
    using Server-Sent Events (SSE). Each chunk includes content, sequence number,
    and final flag. Requires authentication — user_id is derived from the JWT token.

    Args:
        request: ChatRequest with message, optional model/max_tokens, conversation_id
        http_request: FastAPI request object for metadata
        current_user: Authenticated user from JWT token

    Returns:
        StreamingResponse with SSE content type

    Raises:
        HTTPException: 401 if not authenticated, 400 if validation fails
    """
    # Override user_id from JWT token (ignore any user_id in the request body)
    request.user_id = str(current_user.id)

    # Use correlation ID from middleware if available, otherwise generate
    correlation_id = getattr(http_request.state, "correlation_id", None) or str(uuid4())

    # Bind correlation ID to logger context
    logger = structlog.get_logger()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    logger.info(
        "request_received",
        method=http_request.method,
        path=str(http_request.url.path),
        message_length=len(request.message),
        user_id=request.user_id,
        conversation_id=request.conversation_id,
    )

    # Create streaming response with SSE content type
    # Guardrail exceptions are handled within the stream as SSE error events
    response = StreamingResponse(
        generate_sse_stream_with_timeout(request, correlation_id),
        media_type="text/event-stream",
        headers={
            "X-Correlation-Id": correlation_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    return response
