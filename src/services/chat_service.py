"""Chat service for OpenAI Agents SDK integration."""

import time
from typing import AsyncGenerator
from uuid import UUID

import structlog

from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent

from src.config import get_settings
from src.models.response import StreamChunk


class ChatService:
    """Service for streaming chat completions via OpenAI Agents SDK."""

    def __init__(self) -> None:
        """Initialize the chat service with an agent."""
        settings = get_settings()

        self.agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
            model=settings.openai_model,
        )
        self.logger = structlog.get_logger(__name__)

    async def stream_completion(
        self,
        message: str,
        correlation_id: UUID,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat completion chunks from the LLM.

        Args:
            message: User's input message
            correlation_id: Request tracking UUID
            model: Optional model override
            max_tokens: Optional max tokens override

        Yields:
            StreamChunk objects with content and metadata
        """
        settings = get_settings()
        actual_model = model or settings.openai_model
        actual_max_tokens = max_tokens or settings.max_tokens

        # Create agent with specified model
        agent = Agent(
            name="Assistant",
            instructions="You are a helpful assistant.",
            model=actual_model,
        )

        sequence = 0
        start_time = time.perf_counter()

        self.logger.info(
            "stream_started",
            correlation_id=str(correlation_id),
            model=actual_model,
            max_tokens=actual_max_tokens,
        )

        try:
            result = Runner.run_streamed(agent, input=message)

            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    chunk = StreamChunk(
                        content=event.data.delta,
                        sequence=sequence,
                        is_final=False,
                        correlation_id=correlation_id,
                    )

                    # Log chunk metadata (NOT content for privacy)
                    chunk_time_ms = int((time.perf_counter() - start_time) * 1000)
                    self.logger.debug(
                        "chunk_sent",
                        correlation_id=str(correlation_id),
                        sequence=sequence,
                        content_length=len(event.data.delta),
                        elapsed_ms=chunk_time_ms,
                    )

                    sequence += 1
                    yield chunk

            # Emit final chunk
            final_chunk = StreamChunk(
                content="",
                sequence=sequence,
                is_final=True,
                correlation_id=correlation_id,
            )
            yield final_chunk

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            self.logger.info(
                "stream_completed",
                correlation_id=str(correlation_id),
                sequence_count=sequence + 1,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            self.logger.error(
                "stream_error",
                correlation_id=str(correlation_id),
                error_type=type(e).__name__,
                error_message=str(e),
                duration_ms=duration_ms,
                recovery_action="Retry the request or try with a shorter message",
            )
            raise
