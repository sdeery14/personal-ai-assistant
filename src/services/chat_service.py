"""Chat service for OpenAI Agents SDK integration with memory support."""

import time
from typing import AsyncGenerator, Optional
from uuid import UUID

import structlog

from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent

from src.config import get_settings
from src.models.response import StreamChunk
from src.services.agents import (
    build_orchestrator_instructions,
    build_orchestrator_tools,
)
from src.services.guardrails import validate_input, validate_output

logger = structlog.get_logger(__name__)

# Backward-compatible prompt re-exports — delegate to prompt_service.load_prompt()
# so existing test imports continue to work while loading from the registry.
from src.prompts.defaults import PROMPT_DEFAULTS as _PROMPT_DEFAULTS  # noqa: E402

ORCHESTRATOR_BASE_PROMPT = _PROMPT_DEFAULTS["orchestrator-base"]
ONBOARDING_SYSTEM_PROMPT = _PROMPT_DEFAULTS["onboarding"]
PROACTIVE_GREETING_PROMPT = _PROMPT_DEFAULTS["proactive-greeting"]
MEMORY_SYSTEM_PROMPT = _PROMPT_DEFAULTS["memory"]
MEMORY_WRITE_SYSTEM_PROMPT = _PROMPT_DEFAULTS["memory-write"]
WEATHER_SYSTEM_PROMPT = _PROMPT_DEFAULTS["weather"]
GRAPH_SYSTEM_PROMPT = _PROMPT_DEFAULTS["knowledge-graph"]
CALIBRATION_SYSTEM_PROMPT = _PROMPT_DEFAULTS["calibration"]
SCHEDULE_SYSTEM_PROMPT = _PROMPT_DEFAULTS["schedule"]
OBSERVATION_SYSTEM_PROMPT = _PROMPT_DEFAULTS["observation"]
NOTIFICATION_SYSTEM_PROMPT = _PROMPT_DEFAULTS["notification"]


class ChatService:
    """Service for streaming chat completions via OpenAI Agents SDK."""

    def __init__(self) -> None:
        """Initialize the chat service."""
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

    def create_agent(
        self,
        model: str | None = None,
        user_id: str | None = None,
        is_onboarded: bool | None = None,
    ) -> Agent:
        """Create the orchestrator agent with specialist sub-agents as tools.

        This is the single source of truth for agent configuration. Used by both
        the streaming API and the evaluation framework.

        Args:
            model: Optional model override (defaults to OPENAI_MODEL setting).
            user_id: Optional user ID for personalized prompt selection.
            is_onboarded: Optional onboarding status. If None and user_id provided,
                will be checked asynchronously before this call.

        Returns:
            Configured orchestrator Agent with guardrails and specialist tools.
        """
        settings = get_settings()
        actual_model = model or settings.openai_model

        # Trigger lazy-load of conversation service to set _database_available
        _ = self.conversation_service

        # Build specialist tools and orchestrator instructions
        tools, availability = build_orchestrator_tools(actual_model)
        instructions = build_orchestrator_instructions(is_onboarded, availability)

        return Agent(
            name="Assistant",
            instructions=instructions,
            model=actual_model,
            input_guardrails=[validate_input],
            output_guardrails=[validate_output],
            tools=tools,
        )

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

        # Detect greeting mode: empty message triggers auto-greeting
        is_greeting = not message

        # Trigger lazy-load of conversation service to set _database_available.
        # Must happen before the onboarding check below, even for greetings.
        _ = self.conversation_service

        # Try to persist conversation and message (skip for greetings — ephemeral until user engages)
        conversation = None
        if not is_greeting and self._database_available:
            try:
                conversation = await self.conversation_service.get_or_create_conversation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                )
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

        # Feature 011: Check onboarding status for personalized prompts
        is_onboarded = None
        if self._database_available and user_id != "anonymous":
            try:
                from src.services.proactive_service import ProactiveService
                proactive_service = ProactiveService()
                is_onboarded = await proactive_service.is_onboarded(user_id)
            except Exception as e:
                self.logger.warning(
                    "onboarding_check_failed",
                    error=str(e),
                    user_id=user_id,
                )

        # Create the production agent with all features
        agent = self.create_agent(model=actual_model, user_id=user_id, is_onboarded=is_onboarded)

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
            # Pass context for tools to access user_id, correlation_id, and conversation_id
            context = {
                "correlation_id": correlation_id,
                "user_id": user_id,
                "conversation_id": str(conversation.id) if conversation else None,
            }
            # For auto-greetings, use a synthetic instruction instead of empty string
            agent_input = (
                "[System: The user just opened a new conversation. Greet them according to your instructions.]"
                if is_greeting
                else message
            )
            result = Runner.run_streamed(agent, input=agent_input, context=context)

            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    chunk = StreamChunk(
                        content=event.data.delta,
                        sequence=sequence,
                        is_final=False,
                        correlation_id=correlation_id,
                        conversation_id=str(conversation.id) if conversation else None,
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
                conversation_id=str(conversation.id) if conversation else None,
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
                    # Trigger episode summarization if thresholds met
                    try:
                        from src.services.memory_write_service import (
                            MemoryWriteService,
                            schedule_write,
                        )

                        write_service = MemoryWriteService()
                        messages = await self.conversation_service.get_conversation_messages(
                            conversation.id, limit=50
                        )
                        user_msg_count = sum(
                            1 for m in messages if m.role.value == "user"
                        )
                        total_msg_count = len(messages)
                        settings = get_settings()

                        if (
                            user_msg_count >= settings.episode_user_message_threshold
                            or total_msg_count >= settings.episode_total_message_threshold
                        ):
                            schedule_write(
                                write_service.create_episode_summary(
                                    conversation.id, user_id, correlation_id
                                )
                            )
                    except Exception as ep_e:
                        self.logger.warning(
                            "episode_trigger_failed",
                            error=str(ep_e),
                            correlation_id=str(correlation_id),
                        )

                except Exception as e:
                    self.logger.warning(
                        "response_persistence_failed",
                        error=str(e),
                        correlation_id=str(correlation_id),
                    )

            # Feature 011: Mark user as onboarded after first real message (not greeting)
            if not is_greeting and is_onboarded is False and user_id != "anonymous":
                try:
                    from src.services.proactive_service import ProactiveService
                    from src.services.memory_write_service import schedule_write

                    async def _mark_onboarded():
                        ps = ProactiveService()
                        await ps.mark_onboarded(user_id)

                    schedule_write(_mark_onboarded())
                except Exception as e:
                    self.logger.warning(
                        "mark_onboarded_failed",
                        error=str(e),
                        user_id=user_id,
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
