"""Extract agent configuration metadata for storage in MLflow LoggedModel tags.

This module captures the full agent configuration (model, system prompt, tools,
guardrails, specialist agents) as structured metadata by constructing the agent
hierarchy the same way the production code does. This metadata is stored as tags
on the LoggedModel so the eval dashboard can display exactly what was evaluated.
"""

import json
from typing import Any

from src.config import get_settings
from src.services.agents import (
    build_orchestrator_instructions,
    build_orchestrator_tools,
    create_knowledge_agent,
    create_memory_agent,
    create_notification_agent,
    create_proactive_agent,
    create_weather_agent,
)


# Map of specialist factory → (name, tool_name)
_SPECIALIST_FACTORIES = [
    ("MemoryAgent", "ask_memory_agent", create_memory_agent,
     "Delegate to the memory specialist for retrieving, saving, or deleting user memories."),
    ("KnowledgeAgent", "ask_knowledge_agent", create_knowledge_agent,
     "Delegate to the knowledge graph specialist for entities and relationships."),
    ("WeatherAgent", "ask_weather_agent", create_weather_agent,
     "Delegate to the weather specialist for weather queries and forecasts."),
    ("ProactiveAgent", "ask_proactive_agent", create_proactive_agent,
     "Delegate to the proactive assistant for patterns, schedules, and calibration."),
    ("NotificationAgent", "ask_notification_agent", create_notification_agent,
     "Delegate to the notification specialist for persistent notifications."),
]


def extract_agent_metadata(model: str | None = None) -> dict[str, str]:
    """Extract the full agent configuration as a dict of MLflow-safe tag values.

    Returns a flat dict where values are strings (MLflow tag requirement).
    Complex structures are JSON-encoded.
    """
    settings = get_settings()
    actual_model = model or settings.openai_model

    metadata: dict[str, str] = {}

    # Core model config
    metadata["agent.model"] = actual_model
    metadata["agent.name"] = "Assistant"
    metadata["agent.framework"] = "openai-agents-sdk"
    metadata["agent.max_tokens"] = str(settings.max_tokens)
    metadata["agent.timeout_seconds"] = str(settings.timeout_seconds)

    # Build tools and instructions the same way production does
    _tools, availability = build_orchestrator_tools(actual_model)
    instructions = build_orchestrator_instructions(True, availability)

    # System prompt (truncated if too long for MLflow tags — 5000 char limit)
    if len(instructions) > 5000:
        metadata["agent.system_prompt"] = instructions[:4990] + "\n[truncated]"
    else:
        metadata["agent.system_prompt"] = instructions

    # Guardrails (hardcoded — matches ChatService.create_agent)
    guardrails = [
        {"name": "validate_input", "type": "input"},
        {"name": "validate_output", "type": "output"},
    ]
    metadata["agent.guardrails"] = json.dumps(guardrails)

    # Build specialist info by introspecting the actual agent factories
    specialists: list[dict[str, Any]] = []
    for agent_name, tool_name, factory, description in _SPECIALIST_FACTORIES:
        agent = factory(actual_model)
        if agent is None:
            continue

        tool_names = [getattr(t, "name", str(t)) for t in (agent.tools or [])]
        specialists.append({
            "name": tool_name,
            "type": "agent",
            "model": actual_model,
            "tools": tool_names,
            "description": description,
            "agent_name": agent_name,
        })

    metadata["agent.specialists"] = json.dumps(specialists)

    # Build the agent graph structure for visualization
    graph = _build_agent_graph("Assistant", specialists)
    metadata["agent.graph"] = json.dumps(graph)

    return metadata


def _build_agent_graph(
    orchestrator_name: str,
    specialists: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a graph structure describing the agent hierarchy.

    Returns a dict with nodes and edges suitable for frontend visualization.
    """
    nodes: list[dict[str, Any]] = [
        {
            "id": "orchestrator",
            "label": orchestrator_name,
            "type": "orchestrator",
        }
    ]
    edges = []

    for i, spec in enumerate(specialists):
        node_id = f"specialist-{i}"
        node: dict[str, Any] = {
            "id": node_id,
            "label": spec.get("agent_name", spec["name"]),
            "type": "agent",
        }
        if spec.get("tools"):
            node["tools"] = spec["tools"]
        nodes.append(node)
        edges.append({
            "from": "orchestrator",
            "to": node_id,
            "label": "delegates",
        })

    return {"nodes": nodes, "edges": edges}
