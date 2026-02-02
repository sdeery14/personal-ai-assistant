"""Chat service for OpenAI Agents SDK integration with memory support."""

import time
from typing import AsyncGenerator, Optional
from uuid import UUID

import structlog

from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent

from src.config import get_settings
from src.models.response import StreamChunk
from src.services.guardrails import validate_input, validate_output

logger = structlog.get_logger(__name__)

# Memory system prompt guidance (from spec)
MEMORY_SYSTEM_PROMPT = """
You have access to a memory query tool that can retrieve relevant information from past conversations with this user.

When to use memory:
- User references something discussed previously ("like I mentioned", "remember when")
- User asks about their preferences or past decisions
- Personalization would improve the response quality

When using retrieved memories:
- Treat memories as advisory context, not authoritative fact
- Cite memory sources naturally (e.g., "Based on what you mentioned before...")
- If memory seems outdated or contradicts current context, acknowledge the discrepancy
- Never fabricate memories that weren't retrieved
"""

# Weather system prompt guidance (Feature 005)
WEATHER_SYSTEM_PROMPT = """
You have access to a weather tool that can retrieve current conditions and forecasts.

When to use the weather tool:
- User asks about current weather in a location
- User asks about upcoming weather or forecasts
- User asks weather-related questions ("Is it raining?", "Do I need an umbrella?")

When using weather data:
- Present facts without advice or recommendations
- If forecast requested beyond 7 days, explain the limitation
- If location is ambiguous, ask for clarification or note which location was used
- If weather cannot be retrieved, explain the issue and suggest trying again
"""


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
        self._conversation_service = None
        self._database_available = False

    @property
    def conversation_service(self):
        """Lazy-load conversation service."""
        if self._conversation_service is None:
            try:
                from src.services.conversation_service import ConversationService
                self._conversation_service = ConversationService()
                self._database_available = True
            except Exception as e:
                self.logger.warning("conversation_service_unavailable", error=str(e))
                self._database_available = False
        return self._conversation_service

    def _get_tools(self):
        """Get available tools for the agent."""
        tools = []
        # Memory tool (Feature 004)
        try:
            from src.tools.query_memory import query_memory_tool
            tools.append(query_memory_tool)
        except Exception as e:
            self.logger.warning("query_memory_tool_unavailable", error=str(e))
        # Weather tool (Feature 005)
        try:
            from src.tools.get_weather import get_weather_tool
            tools.append(get_weather_tool)
            self._weather_available = True
        except Exception as e:
            self.logger.warning("get_weather_tool_unavailable", error=str(e))
            self._weather_available = False
        return tools

    async def stream_completion(
        self,
        message: str,
        correlation_id: UUID,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        user_id: str = "anonymous",
        conversation_id: Optional[str] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream chat completion chunks from the LLM.

        Args:
            message: User's input message
            correlation_id: Request tracking UUID
            model: Optional model override
            max_tokens: Optional max tokens override
            user_id: User identifier for memory scoping
            conversation_id: Optional existing conversation ID

        Yields:
            StreamChunk objects with content and metadata
        """
        settings = get_settings()
        actual_model = model or settings.openai_model
        actual_max_tokens = max_tokens or settings.max_tokens

        # Try to persist conversation and message
        conversation = None
        if self.conversation_service and self._database_available:
            try:
                conversation = await self.conversation_service.get_or_create_conversation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                )
                # Persist user message
                await self.conversation_service.add_message(
                    conversation_id=conversation.id,
                    role="user",
                    content=message,
                    correlation_id=correlation_id,
                )
            except Exception as e:
                self.logger.warning(
                    "conversation_persistence_failed",
                    error=str(e),
                    correlation_id=str(correlation_id),
                )
                conversation = None

        # Build system instructions with feature-specific guidance
        instructions = "You are a helpful assistant."
        if self._database_available:
            instructions += "\n" + MEMORY_SYSTEM_PROMPT

        # Get tools - weather tool is always available, memory requires database
        tools = self._get_tools()
        if hasattr(self, '_weather_available') and self._weather_available:
            instructions += "\n" + WEATHER_SYSTEM_PROMPT

        # Create agent with input and output guardrails and tools
        agent = Agent(
            name="Assistant",
            instructions=instructions,
            model=actual_model,
            input_guardrails=[validate_input],
            output_guardrails=[validate_output],
            tools=tools,
        )

        sequence = 0
        start_time = time.perf_counter()
        accumulated_response = []

        self.logger.info(
            "stream_started",
            correlation_id=str(correlation_id),
            model=actual_model,
            max_tokens=actual_max_tokens,
            user_id=user_id,
            conversation_id=str(conversation.id) if conversation else None,
            memory_enabled=self._database_available,
        )

        try:
            # Pass context for tools to access user_id and correlation_id
            context = {
                "correlation_id": correlation_id,
                "user_id": user_id,
            }
            result = Runner.run_streamed(agent, input=message, context=context)

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

                    # Accumulate response for persistence
                    accumulated_response.append(event.data.delta)

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

            # Persist assistant response
            if conversation and self._database_available:
                try:
                    full_response = "".join(accumulated_response)
                    await self.conversation_service.add_message(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=full_response,
                        correlation_id=correlation_id,
                        generate_embedding=False,  # Don't embed assistant responses for now
                    )
                except Exception as e:
                    self.logger.warning(
                        "response_persistence_failed",
                        error=str(e),
                        correlation_id=str(correlation_id),
                    )

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
