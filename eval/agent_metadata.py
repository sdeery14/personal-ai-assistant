"""Extract agent configuration metadata for storage in MLflow LoggedModel tags.

This module introspects the production agent to capture its full configuration
(model, system prompt, tools, guardrails, specialist agents) as structured
metadata. This metadata is stored as tags on the LoggedModel so the eval
dashboard can display exactly what was evaluated.
"""

import json
from typing import Any

from src.config import get_settings
from src.services.chat_service import ChatService


def extract_agent_metadata(model: str | None = None) -> dict[str, str]:
    """Extract the full agent configuration as a dict of MLflow-safe tag values.

    Returns a flat dict where values are strings (MLflow tag requirement).
    Complex structures are JSON-encoded.
    """
    settings = get_settings()
    actual_model = model or settings.openai_model

    # Create the agent to introspect it
    service = ChatService()
    agent = service.create_agent(model=actual_model, is_onboarded=True)

    # Extract orchestrator config
    metadata: dict[str, str] = {}

    # Core model config
    metadata["agent.model"] = agent.model
    metadata["agent.name"] = agent.name
    metadata["agent.framework"] = "openai-agents-sdk"
    metadata["agent.max_tokens"] = str(settings.max_tokens)
    metadata["agent.timeout_seconds"] = str(settings.timeout_seconds)

    # System prompt (truncated if too long for MLflow tags — 5000 char limit)
    instructions = agent.instructions if isinstance(agent.instructions, str) else ""
    if len(instructions) > 5000:
        metadata["agent.system_prompt"] = instructions[:4990] + "\n[truncated]"
    else:
        metadata["agent.system_prompt"] = instructions

    # Guardrails
    guardrails = []
    if agent.input_guardrails:
        for g in agent.input_guardrails:
            guardrails.append({
                "name": getattr(g, "name", str(g)),
                "type": "input",
            })
    if agent.output_guardrails:
        for g in agent.output_guardrails:
            guardrails.append({
                "name": getattr(g, "name", str(g)),
                "type": "output",
            })
    metadata["agent.guardrails"] = json.dumps(guardrails)

    # Extract specialist agents and their tools from the orchestrator's tools
    specialists: list[dict[str, Any]] = []
    for tool in agent.tools:
        spec: dict[str, Any] = {
            "name": getattr(tool, "name", str(tool)),
        }
        # Agent-as-tool wraps an Agent object
        inner_agent = getattr(tool, "agent", None)
        if inner_agent is not None:
            spec["type"] = "agent"
            spec["model"] = getattr(inner_agent, "model", actual_model)
            # Extract the specialist's own tools
            inner_tools = getattr(inner_agent, "tools", [])
            spec["tools"] = [
                getattr(t, "name", str(t)) for t in inner_tools
            ]
            # Brief description from tool_description
            spec["description"] = getattr(tool, "description", "")
        else:
            spec["type"] = "function"
            spec["description"] = getattr(tool, "description", "")

        specialists.append(spec)

    metadata["agent.specialists"] = json.dumps(specialists)

    # Build the agent graph structure for visualization
    graph = _build_agent_graph(agent.name, specialists)
    metadata["agent.graph"] = json.dumps(graph)

    return metadata


def _build_agent_graph(
    orchestrator_name: str,
    specialists: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a graph structure describing the agent hierarchy.

    Returns a dict with nodes and edges suitable for frontend visualization.
    """
    nodes = [
        {
            "id": "orchestrator",
            "label": orchestrator_name,
            "type": "orchestrator",
        }
    ]
    edges = []

    for i, spec in enumerate(specialists):
        node_id = f"specialist-{i}"
        node = {
            "id": node_id,
            "label": spec["name"],
            "type": spec.get("type", "function"),
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
