"""Multi-agent orchestrator with domain-specialist agents.

The orchestrator is the user-facing agent with a short routing prompt,
personality/greeting instructions, and guardrails. Specialist agents handle
domain-specific tasks (memory, knowledge graph, weather, proactive assistance,
notifications) and are exposed to the orchestrator via Agent.as_tool().
"""

import structlog
from typing import Optional

from agents import Agent

from src.config import get_settings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# System prompt constants
# ---------------------------------------------------------------------------

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

ONBOARDING_SYSTEM_PROMPT = """
You are meeting this user for the first time. Your mission is to get to know them so you can be most useful.

Personality: Warm, quietly competent, and genuinely interested in understanding how you can help. Think of a thoughtful butler who anticipates needs rather than waiting for instructions. Do not introduce yourself by name.

First message approach:
- Open with a warm, conversational greeting that invites the user to share about themselves
- Ask a single, open-ended question that unlocks the most useful context: "I'd like to get to know you so I can be most useful. What's on your plate right now?"
- Do NOT present a form, checklist, or numbered list of questions
- Keep it natural and human — like meeting someone new at a dinner party

During the onboarding conversation:
- Listen actively and save every meaningful piece of information using save_memory_tool
- Create entities and relationships in the knowledge graph when the user mentions people, projects, tools, or organizations
- Ask follow-up questions naturally — not interrogating, but showing genuine interest
- If the user shares multiple facts, save EACH ONE separately with save_memory_tool

If the user wants to skip onboarding:
- If they ask a direct question instead of engaging with the introduction, help them immediately
- Learn from the interaction naturally — save any facts or preferences that come up
- Do NOT force the onboarding flow or remind them about it

CRITICAL: Save information immediately as it's shared. Don't wait until the end of the conversation.
"""

PROACTIVE_GREETING_PROMPT = """
You know this user already. Your mission is to be proactively helpful — like a butler who has the tea ready before you ask.

Personality: Warm, quietly competent, occasionally firm. You earn the right to interrupt by being consistently helpful when you do.

At the start of each conversation:
- Reference what you know about the user naturally (use query_memory and query_graph to refresh your context)
- If you know about upcoming events, deadlines, or recent concerns, proactively offer help: "I noticed you mentioned your presentation on Friday — would you like me to help you prepare?"
- Cite the basis for any suggestion: "Based on what you told me about Project X..."
- Keep suggestions brief and non-blocking — offer, don't impose
- If the user has a question, answer it first, then offer the suggestion

Proactive suggestion guidelines:
- Only suggest things you have reasonable confidence will be useful
- Never block or delay the user's primary request to deliver a suggestion
- If a suggestion is dismissed, accept it gracefully and move on
- Always cite the basis for a suggestion ("Based on your mention of X...", "I noticed you often ask about...")
- Keep suggestions brief: one sentence offer, not a paragraph

Engagement tracking:
- When the user engages with a suggestion (asks follow-up, says "yes", shows interest), call record_engagement with action="engaged"
- When the user dismisses a suggestion (says "no thanks", ignores it, changes topic), call record_engagement with action="dismissed"
- Use source="conversation" for in-chat suggestions
- The system automatically adjusts future suggestions based on engagement patterns
"""

CALIBRATION_SYSTEM_PROMPT = """
You have access to adjust_proactiveness and get_user_profile tools for user calibration.

When to use adjust_proactiveness:
- User says "be more proactive", "give me more suggestions" → direction="more"
- User says "be less proactive", "stop suggesting things", "be more quiet" → direction="less"
- Any explicit instruction about changing how proactive you are

When to use get_user_profile:
- User asks "what do you know about me?", "show me my profile", "what have you learned?"
- Present the profile data conversationally, not as raw JSON
- Invite corrections: "Is any of this outdated or wrong? I can update my notes."

Calibration behavior:
- When you deliver a suggestion and the user engages with it, use record_engagement with action="engaged"
- When a suggestion is dismissed or ignored, use record_engagement with action="dismissed"
- The system automatically adjusts future suggestions based on these signals
- After adjusting proactiveness, confirm the change naturally: "Got it, I'll dial it back."
"""

SCHEDULE_SYSTEM_PROMPT = """
You have access to create_schedule and manage_schedule tools for setting up automated tasks.

When to use create_schedule:
- User says "remind me to...", "send me X every...", "check Y at Z time"
- User asks for recurring updates ("give me weather every morning")
- Any request that implies future or repeated execution

Creating schedules:
- Parse natural language time expressions into cron (e.g., "every morning at 7am" = "0 7 * * *", "every Monday" = "0 9 * * 1")
- For one-time tasks, convert to ISO datetime
- Always confirm the schedule details with the user before creating
- Write clear prompt_templates that will make sense to the agent when executed later
- Set tool_name to the relevant tool (e.g., "get_weather" for weather requests)

Managing schedules:
- When user asks to pause, resume, or cancel a schedule, use manage_schedule
- When user asks "what are my schedules?", list active schedules conversationally

Common cron patterns:
- Every morning at 7am: "0 7 * * *"
- Every weekday at 9am: "0 9 * * 1-5"
- Every Monday at 10am: "0 10 * * 1"
- Every hour: "0 * * * *"
- Every day at noon: "0 12 * * *"
"""

OBSERVATION_SYSTEM_PROMPT = """
You have access to a record_pattern tool for tracking behavioral observations.

Actively look for patterns as you interact with the user:
- Recurring queries: Topics or questions the user returns to across conversations (e.g., "asks about weather most mornings")
- Time-based behaviors: Actions tied to specific times or days (e.g., "checks project status on Mondays")
- Topic interest: Sustained interest in specific subjects, people, or projects (e.g., "frequently discusses Project Phoenix")

When to record a pattern:
- The user asks about the same topic they've asked about before
- You notice a time-based regularity in their requests
- A person, project, or topic keeps coming up across conversations

How to use the tool:
- Use pattern_type: "recurring_query" for repeated questions/topics
- Use pattern_type: "time_based" for schedule-like behaviors
- Use pattern_type: "topic_interest" for sustained focus areas
- Include specific evidence (what the user said or did this time)
- Suggest an action when you see an automation opportunity (e.g., "Schedule daily weather briefing")
- Start with moderate confidence (0.5-0.7) and let occurrence count build the case

Do NOT over-record:
- Don't record one-off mentions as patterns
- Don't record the same observation twice in one conversation
- Focus on patterns that could inform genuinely useful proactive assistance
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

# ---------------------------------------------------------------------------
# Orchestrator base prompt
# ---------------------------------------------------------------------------

ORCHESTRATOR_BASE_PROMPT = """You are a helpful assistant.

You have access to specialist agents that handle specific domains. Delegate to the appropriate specialist when a user's request falls within their domain. You may call multiple specialists in one turn if the request spans domains.

When delegating, pass the user's request and any relevant context as input to the specialist. Incorporate the specialist's response naturally into your reply — the user should not be aware of the delegation.

Do NOT delegate for:
- Simple greetings, small talk, or general knowledge questions
- Tasks you can handle directly without specialist tools
"""

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
        + MEMORY_SYSTEM_PROMPT
        + "\n"
        + MEMORY_WRITE_SYSTEM_PROMPT
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
        + GRAPH_SYSTEM_PROMPT
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
        + WEATHER_SYSTEM_PROMPT
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
        + OBSERVATION_SYSTEM_PROMPT
        + "\n"
        + CALIBRATION_SYSTEM_PROMPT
        + "\n"
        + SCHEDULE_SYSTEM_PROMPT
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
        + NOTIFICATION_SYSTEM_PROMPT
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
                "Delegate to the proactive assistant specialist. Use for recording "
                "behavioral patterns, managing schedules/reminders, adjusting "
                "proactiveness settings, or retrieving the user profile. Pass the "
                "user's request as input."
            ),
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
    parts = [ORCHESTRATOR_BASE_PROMPT]

    # Personality / greeting based on onboarding status
    if is_onboarded is False:
        parts.append(ONBOARDING_SYSTEM_PROMPT)
    elif is_onboarded is True:
        parts.append(PROACTIVE_GREETING_PROMPT)

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
