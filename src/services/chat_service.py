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

MEMORY_WRITE_SYSTEM_PROMPT = """
You MUST use save_memory_tool to remember important user information. This is a core responsibility.

ALWAYS CALL save_memory_tool when the user shares:
- Personal facts: name, location, job/role, company, family members, pets, hobbies
  Example: "I'm a software engineer at Google" → CALL save_memory_tool(content="User is a software engineer at Google", memory_type="fact", confidence=0.95)
- Preferences: likes, dislikes, tool preferences, editor settings, formatting preferences
  Example: "I prefer dark mode and tabs over spaces" → CALL save_memory_tool for EACH preference separately
- Decisions: technology choices, commitments, plans, project decisions
  Example: "I've decided to use PostgreSQL" → CALL save_memory_tool(content="User decided to use PostgreSQL for their database", memory_type="decision", confidence=0.95)
- Project context: what they're building, tech stack, goals
  Example: "I'm building a finance app with React Native" → CALL save_memory_tool(content="User is building a personal finance app using React Native", memory_type="note", confidence=0.9)

DO NOT SAVE trivial content:
- Greetings: "Hello", "Hi there", "How are you?"
- Thanks: "Thanks!", "Thank you for your help"
- Simple acknowledgments: "OK", "Got it", "Sounds good"
- Uncertain/hypothetical: "I might...", "I'm thinking maybe...", "not sure yet"

Confidence scoring:
- 0.9-1.0: Explicit statements ("My name is...", "I live in...", "I prefer...", "I've decided...")
- 0.8-0.9: Clear implications ("I'm building X with Y" = tech decisions)
- 0.7-0.8: Reasonable inference with context

Memory types:
- "fact": Personal info (name, location, job, family, pets)
- "preference": Likes, dislikes, settings, style choices
- "decision": Explicit choices, commitments, selections
- "note": Project context, goals, background

For CORRECTIONS (user updates info):
1. SAVE the new information with save_memory_tool
2. DELETE the old with delete_memory_tool
Example: "Actually I moved to Seattle" → save Seattle location, delete old location

For DELETIONS:
- Use delete_memory_tool when user says "forget", "remove", "delete"

CRITICAL: Call save_memory_tool for EACH distinct piece of memorable information. Multiple facts = multiple tool calls.
"""

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

GRAPH_SYSTEM_PROMPT = """
You have access to knowledge graph tools for tracking entities and relationships.

ENTITY EXTRACTION - Use save_entity when user mentions specific:
- People: "Sarah", "my manager Dave", "my friend John" → type: person
- Projects: "project Phoenix", "the API rewrite", "my startup" → type: project
- Tools: "FastAPI", "PostgreSQL", "React", "Docker" → type: tool
- Concepts: "microservices", "TDD", "agile methodology" → type: concept
- Organizations: "Google", "the backend team", "my company" → type: organization

RELATIONSHIP EXTRACTION - Use save_relationship when user expresses:
- "I use FastAPI" → USES relationship (source: user context, target: FastAPI/tool)
- "I prefer Python over JavaScript" → PREFERS relationship
- "I work with Sarah" → WORKS_WITH relationship
- "Project Phoenix uses PostgreSQL" → USES relationship between entities
- "I've decided on React" → DECIDED relationship
- "I work on the backend" → WORKS_ON relationship

QUERYING - Use query_graph when user asks about relationships:
- "What tools do I use?" → query for USES relationships
- "Who do I work with?" → query for WORKS_WITH relationships
- "What technologies does my project use?" → query about project relationships

Confidence scoring for extraction:
- 0.9-1.0: Explicit mentions ("I use FastAPI", "Sarah is my colleague")
- 0.8-0.9: Clear context ("we're building with React" = project USES React)
- 0.7-0.8: Reasonable inference from context

Extract entities and relationships naturally as they come up in conversation. Don't force extraction for trivial mentions.
"""

NOTIFICATION_SYSTEM_PROMPT = """
You have access to a send_notification tool that creates persistent notifications for the user.

When to send notifications:
- User explicitly asks to be reminded about something ("remind me to...", "don't let me forget...")
- You identify time-sensitive or important information worth flagging ("your meeting is in 30 minutes")
- Warnings about potential issues ("your API key expires next week")

When NOT to send notifications:
- For information that's part of the current conversation flow (just say it directly)
- For trivial acknowledgments or greetings
- When the user hasn't indicated they want to be notified

Notification types:
- "reminder": Time-based or task-based reminders the user requested
- "info": Useful information worth surfacing later
- "warning": Potential issues or problems that need attention

Guidelines:
- Keep notification messages concise and actionable (under 500 characters)
- One notification per distinct piece of information
- Don't send duplicate notifications for the same thing
- Respect that notifications persist beyond the conversation — write them to be understandable out of context
"""


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

    def _get_tools(self):
        """Get available tools for the agent."""
        tools = []
        # Memory tool (Feature 004)
        try:
            from src.tools.query_memory import query_memory_tool
            tools.append(query_memory_tool)
        except Exception as e:
            self.logger.warning("query_memory_tool_unavailable", error=str(e))
        # Memory write tools (Feature 006)
        try:
            from src.tools.save_memory import save_memory_tool
            tools.append(save_memory_tool)
        except Exception as e:
            self.logger.warning("save_memory_tool_unavailable", error=str(e))
        try:
            from src.tools.delete_memory import delete_memory_tool
            tools.append(delete_memory_tool)
        except Exception as e:
            self.logger.warning("delete_memory_tool_unavailable", error=str(e))
        # Knowledge Graph tools (Feature 007)
        try:
            from src.tools.save_entity import save_entity_tool
            tools.append(save_entity_tool)
            self._graph_available = True
        except Exception as e:
            self.logger.warning("save_entity_tool_unavailable", error=str(e))
            self._graph_available = False
        try:
            from src.tools.save_relationship import save_relationship_tool
            tools.append(save_relationship_tool)
        except Exception as e:
            self.logger.warning("save_relationship_tool_unavailable", error=str(e))
        try:
            from src.tools.query_graph import query_graph_tool
            tools.append(query_graph_tool)
        except Exception as e:
            self.logger.warning("query_graph_tool_unavailable", error=str(e))
        # Weather tool (Feature 005)
        try:
            from src.tools.get_weather import get_weather_tool
            tools.append(get_weather_tool)
            self._weather_available = True
        except Exception as e:
            self.logger.warning("get_weather_tool_unavailable", error=str(e))
            self._weather_available = False
        # Notification tool (Feature 010)
        try:
            from src.tools.send_notification import send_notification_tool
            tools.append(send_notification_tool)
            self._notifications_available = True
        except Exception as e:
            self.logger.warning("send_notification_tool_unavailable", error=str(e))
            self._notifications_available = False
        return tools

    def create_agent(self, model: str | None = None) -> Agent:
        """Create the production agent with all tools, guardrails, and instructions.

        This is the single source of truth for agent configuration. Used by both
        the streaming API and the evaluation framework.

        Args:
            model: Optional model override (defaults to OPENAI_MODEL setting).

        Returns:
            Configured Agent with guardrails, tools, and system prompts.
        """
        settings = get_settings()
        actual_model = model or settings.openai_model

        # Trigger lazy-load of conversation service to set _database_available
        _ = self.conversation_service

        # Build system instructions with feature-specific guidance
        instructions = "You are a helpful assistant."
        if self._database_available:
            instructions += "\n" + MEMORY_SYSTEM_PROMPT
            instructions += "\n" + MEMORY_WRITE_SYSTEM_PROMPT

        # Get tools - sets _weather_available and _graph_available as side effects
        tools = self._get_tools()
        if getattr(self, '_weather_available', False):
            instructions += "\n" + WEATHER_SYSTEM_PROMPT
        if getattr(self, '_graph_available', False):
            instructions += "\n" + GRAPH_SYSTEM_PROMPT
        if getattr(self, '_notifications_available', False):
            instructions += "\n" + NOTIFICATION_SYSTEM_PROMPT

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

        # Create the production agent with all features
        agent = self.create_agent(model=actual_model)

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
