"""Multi-agent orchestrator with domain-specialist agents.

The orchestrator is the user-facing agent with a short routing prompt,
personality/greeting instructions, and guardrails. Specialist agents handle
domain-specific tasks (memory, knowledge graph, weather, proactive assistance,
notifications) and are exposed to the orchestrator via Agent.as_tool().
"""

import structlog
from typing import Optional

from agents import Agent, RunConfig

from src.config import get_settings
from src.services.prompt_service import load_prompt

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Tool loading helpers (one per specialist domain)
# ---------------------------------------------------------------------------


def _load_memory_tools() -> list:
    """Load memory-related tools. Returns empty list on failure."""
    tools = []
    try:
        from src.tools.query_memory import query_memory_tool
        tools.append(query_memory_tool)
    except Exception as e:
        logger.warning("query_memory_tool_unavailable", error=str(e))
    try:
        from src.tools.save_memory import save_memory_tool
        tools.append(save_memory_tool)
    except Exception as e:
        logger.warning("save_memory_tool_unavailable", error=str(e))
    try:
        from src.tools.delete_memory import delete_memory_tool
        tools.append(delete_memory_tool)
    except Exception as e:
        logger.warning("delete_memory_tool_unavailable", error=str(e))
    return tools


def _load_knowledge_tools() -> list:
    """Load knowledge graph tools. Returns empty list on failure."""
    tools = []
    try:
        from src.tools.save_entity import save_entity_tool
        tools.append(save_entity_tool)
    except Exception as e:
        logger.warning("save_entity_tool_unavailable", error=str(e))
    try:
        from src.tools.save_relationship import save_relationship_tool
        tools.append(save_relationship_tool)
    except Exception as e:
        logger.warning("save_relationship_tool_unavailable", error=str(e))
    try:
        from src.tools.query_graph import query_graph_tool
        tools.append(query_graph_tool)
    except Exception as e:
        logger.warning("query_graph_tool_unavailable", error=str(e))
    return tools


def _load_weather_tools() -> list:
    """Load weather tools. Returns empty list on failure."""
    try:
        from src.tools.get_weather import get_weather_tool
        return [get_weather_tool]
    except Exception as e:
        logger.warning("get_weather_tool_unavailable", error=str(e))
        return []


def _load_proactive_tools() -> list:
    """Load proactive assistant tools. Returns empty list on failure."""
    tools = []
    try:
        from src.tools.record_pattern import record_pattern
        tools.append(record_pattern)
    except Exception as e:
        logger.warning("record_pattern_tool_unavailable", error=str(e))
    try:
        from src.tools.record_engagement import record_engagement
        tools.append(record_engagement)
    except Exception as e:
        logger.warning("record_engagement_tool_unavailable", error=str(e))
    try:
        from src.tools.create_schedule import create_schedule
        from src.tools.manage_schedule import manage_schedule
        tools.append(create_schedule)
        tools.append(manage_schedule)
    except Exception as e:
        logger.warning("schedule_tools_unavailable", error=str(e))
    try:
        from src.tools.adjust_proactiveness import adjust_proactiveness
        from src.tools.get_user_profile import get_user_profile
        tools.append(adjust_proactiveness)
        tools.append(get_user_profile)
    except Exception as e:
        logger.warning("calibration_tools_unavailable", error=str(e))
    return tools


def _load_notification_tools() -> list:
    """Load notification tools. Returns empty list on failure."""
    try:
        from src.tools.send_notification import send_notification_tool
        return [send_notification_tool]
    except Exception as e:
        logger.warning("send_notification_tool_unavailable", error=str(e))
        return []


# ---------------------------------------------------------------------------
# Specialist agent factories
# ---------------------------------------------------------------------------


def create_memory_agent(model: str) -> Optional[Agent]:
    """Create the memory specialist agent, or None if no tools loaded."""
    tools = _load_memory_tools()
    if not tools:
        return None
    instructions = (
        "You are a memory specialist. You retrieve, save, and delete user memories.\n"
        + load_prompt("memory")
        + "\n"
        + load_prompt("memory-write")
    )
    return Agent(
        name="MemoryAgent",
        instructions=instructions,
        model=model,
        tools=tools,
    )


def create_knowledge_agent(model: str) -> Optional[Agent]:
    """Create the knowledge graph specialist agent, or None if no tools loaded."""
    tools = _load_knowledge_tools()
    if not tools:
        return None
    instructions = (
        "You are a knowledge graph specialist. You extract and query entities and relationships.\n"
        + load_prompt("knowledge-graph")
    )
    return Agent(
        name="KnowledgeAgent",
        instructions=instructions,
        model=model,
        tools=tools,
    )


def create_weather_agent(model: str) -> Optional[Agent]:
    """Create the weather specialist agent, or None if tool unavailable."""
    tools = _load_weather_tools()
    if not tools:
        return None
    instructions = (
        "You are a weather specialist. You retrieve weather data for locations.\n"
        + load_prompt("weather")
    )
    return Agent(
        name="WeatherAgent",
        instructions=instructions,
        model=model,
        tools=tools,
    )


def create_proactive_agent(model: str) -> Optional[Agent]:
    """Create the proactive assistant specialist, or None if no tools loaded."""
    tools = _load_proactive_tools()
    if not tools:
        return None
    instructions = (
        "You are a proactive assistant specialist. You track patterns, manage schedules, and calibrate proactiveness.\n"
        + load_prompt("observation")
        + "\n"
        + load_prompt("calibration")
        + "\n"
        + load_prompt("schedule")
    )
    return Agent(
        name="ProactiveAgent",
        instructions=instructions,
        model=model,
        tools=tools,
    )


def create_notification_agent(model: str) -> Optional[Agent]:
    """Create the notification specialist agent, or None if tool unavailable."""
    tools = _load_notification_tools()
    if not tools:
        return None
    instructions = (
        "You are a notification specialist. You create persistent notifications for the user.\n"
        + load_prompt("notification")
    )
    return Agent(
        name="NotificationAgent",
        instructions=instructions,
        model=model,
        tools=tools,
    )


# ---------------------------------------------------------------------------
# Orchestrator builders
# ---------------------------------------------------------------------------


def build_orchestrator_tools(model: str) -> tuple[list, dict[str, bool]]:
    """Create specialist agents and wrap them as tools for the orchestrator.

    Returns:
        Tuple of (tools_list, availability_dict) where availability_dict maps
        specialist names to whether they were successfully created.
    """
    tools = []
    availability = {}

    # Disable tracing on sub-agent runs to prevent orphan traces.
    # The orchestrator's trace still records the tool calls; sub-agents
    # just don't create their own separate "Agent workflow" traces.
    sub_agent_config = RunConfig(tracing_disabled=True)

    # Memory specialist
    memory_agent = create_memory_agent(model)
    if memory_agent:
        tools.append(memory_agent.as_tool(
            tool_name="ask_memory_agent",
            tool_description=(
                "Delegate to the memory specialist. Use for retrieving, saving, "
                "updating, or deleting user memories and preferences. Pass the "
                "user's request and relevant context as input."
            ),
            run_config=sub_agent_config,
        ))
        availability["memory"] = True
    else:
        availability["memory"] = False

    # Knowledge graph specialist
    knowledge_agent = create_knowledge_agent(model)
    if knowledge_agent:
        tools.append(knowledge_agent.as_tool(
            tool_name="ask_knowledge_agent",
            tool_description=(
                "Delegate to the knowledge graph specialist. Use for saving or "
                "querying entities (people, projects, tools, organizations) and "
                "their relationships. Pass the user's statement or question as input."
            ),
            run_config=sub_agent_config,
        ))
        availability["knowledge"] = True
    else:
        availability["knowledge"] = False

    # Weather specialist
    weather_agent = create_weather_agent(model)
    if weather_agent:
        tools.append(weather_agent.as_tool(
            tool_name="ask_weather_agent",
            tool_description=(
                "Delegate to the weather specialist. Use when the user asks about "
                "current weather, forecasts, or weather-related questions. Pass "
                "the location and question as input."
            ),
            run_config=sub_agent_config,
        ))
        availability["weather"] = True
    else:
        availability["weather"] = False

    # Proactive assistant specialist
    proactive_agent = create_proactive_agent(model)
    if proactive_agent:
        tools.append(proactive_agent.as_tool(
            tool_name="ask_proactive_agent",
            tool_description=(
                "Delegate to the proactive assistant specialist. MUST be called for: "
                "creating schedules/recurring tasks, setting up reminders, managing "
                "existing schedules. Also used for: recording behavioral patterns, "
                "adjusting proactiveness settings, or retrieving the user profile. "
                "Pass the user's request as input."
            ),
            run_config=sub_agent_config,
        ))
        availability["proactive"] = True
    else:
        availability["proactive"] = False

    # Notification specialist
    notification_agent = create_notification_agent(model)
    if notification_agent:
        tools.append(notification_agent.as_tool(
            tool_name="ask_notification_agent",
            tool_description=(
                "Delegate to the notification specialist. Use when the user wants "
                "to be reminded about something or when you identify information "
                "worth flagging as a persistent notification. Pass the notification "
                "details as input."
            ),
            run_config=sub_agent_config,
        ))
        availability["notification"] = True
    else:
        availability["notification"] = False

    return tools, availability


def build_orchestrator_instructions(
    is_onboarded: Optional[bool],
    availability: dict[str, bool],
) -> str:
    """Assemble orchestrator instructions from base prompt + personality + routing hints.

    Args:
        is_onboarded: User onboarding status. False = new user, True = returning.
        availability: Dict of specialist name → bool from build_orchestrator_tools.

    Returns:
        Complete instruction string for the orchestrator agent.
    """
    parts = [load_prompt("orchestrator-base")]

    # Personality / greeting based on onboarding status
    if is_onboarded is False:
        parts.append(load_prompt("onboarding"))
    elif is_onboarded is True:
        parts.append(load_prompt("proactive-greeting"))

    # Routing hints for available specialists
    routing_hints = []
    if availability.get("memory"):
        routing_hints.append(
            "- ask_memory_agent: For retrieving, saving, or deleting user memories and preferences"
        )
    if availability.get("knowledge"):
        routing_hints.append(
            "- ask_knowledge_agent: For saving/querying entities (people, projects, tools) and relationships"
        )
    if availability.get("weather"):
        routing_hints.append(
            "- ask_weather_agent: For weather queries and forecasts"
        )
    if availability.get("proactive"):
        routing_hints.append(
            "- ask_proactive_agent: For pattern tracking, schedule management, proactiveness calibration, and user profiles"
        )
    if availability.get("notification"):
        routing_hints.append(
            "- ask_notification_agent: For creating persistent notifications and reminders"
        )

    if routing_hints:
        parts.append(
            "\nAvailable specialists:\n" + "\n".join(routing_hints)
        )

    return "\n".join(parts)
