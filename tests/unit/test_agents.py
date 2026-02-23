"""Unit tests for multi-agent orchestrator architecture."""

from unittest.mock import patch

import pytest

from src.services.agents import (
    ONBOARDING_SYSTEM_PROMPT,
    ORCHESTRATOR_BASE_PROMPT,
    PROACTIVE_GREETING_PROMPT,
    build_orchestrator_instructions,
    build_orchestrator_tools,
    create_knowledge_agent,
    create_memory_agent,
    create_notification_agent,
    create_proactive_agent,
    create_weather_agent,
)


class TestSpecialistAgentCreation:
    """Tests for individual specialist agent factory functions."""

    def test_memory_agent_created_with_tools(self):
        """Memory agent should be created when tools load successfully."""
        agent = create_memory_agent("gpt-4")
        assert agent is not None
        assert agent.name == "MemoryAgent"
        tool_names = [t.name for t in agent.tools]
        assert "query_memory_tool" in tool_names
        assert "save_memory_tool" in tool_names
        assert "delete_memory_tool" in tool_names

    def test_knowledge_agent_created_with_tools(self):
        """Knowledge agent should be created when tools load successfully."""
        agent = create_knowledge_agent("gpt-4")
        assert agent is not None
        assert agent.name == "KnowledgeAgent"
        tool_names = [t.name for t in agent.tools]
        assert "save_entity" in tool_names
        assert "save_relationship" in tool_names
        assert "query_graph" in tool_names

    def test_weather_agent_created_with_tool(self):
        """Weather agent should be created when tool loads successfully."""
        agent = create_weather_agent("gpt-4")
        assert agent is not None
        assert agent.name == "WeatherAgent"
        tool_names = [t.name for t in agent.tools]
        assert "get_weather" in tool_names

    def test_proactive_agent_created_with_tools(self):
        """Proactive agent should be created when tools load successfully."""
        agent = create_proactive_agent("gpt-4")
        assert agent is not None
        assert agent.name == "ProactiveAgent"
        tool_names = [t.name for t in agent.tools]
        assert "record_pattern" in tool_names

    def test_notification_agent_created_with_tool(self):
        """Notification agent should be created when tool loads successfully."""
        agent = create_notification_agent("gpt-4")
        assert agent is not None
        assert agent.name == "NotificationAgent"
        tool_names = [t.name for t in agent.tools]
        assert "send_notification" in tool_names

    def test_specialist_returns_none_when_tools_fail(self):
        """Specialist factory returns None when all tools fail to import."""
        with patch(
            "src.services.agents._load_memory_tools", return_value=[]
        ):
            agent = create_memory_agent("gpt-4")
            assert agent is None

    def test_specialist_instructions_contain_domain_prompts(self):
        """Each specialist should have its domain-specific prompts."""
        memory = create_memory_agent("gpt-4")
        assert "memory query tool" in memory.instructions.lower()
        assert "save_memory_tool" in memory.instructions

        knowledge = create_knowledge_agent("gpt-4")
        assert "knowledge graph" in knowledge.instructions.lower()
        assert "save_entity" in knowledge.instructions

        weather = create_weather_agent("gpt-4")
        assert "weather tool" in weather.instructions.lower()


class TestBuildOrchestratorTools:
    """Tests for build_orchestrator_tools function."""

    def test_all_specialists_created(self):
        """All 5 specialist tools should be created when dependencies are available."""
        tools, availability = build_orchestrator_tools("gpt-4")
        assert availability["memory"] is True
        assert availability["knowledge"] is True
        assert availability["weather"] is True
        assert availability["proactive"] is True
        assert availability["notification"] is True
        assert len(tools) == 5

    def test_tool_names_are_correct(self):
        """Orchestrator tools should have ask_*_agent naming pattern."""
        tools, _ = build_orchestrator_tools("gpt-4")
        tool_names = [t.name for t in tools]
        assert "ask_memory_agent" in tool_names
        assert "ask_knowledge_agent" in tool_names
        assert "ask_weather_agent" in tool_names
        assert "ask_proactive_agent" in tool_names
        assert "ask_notification_agent" in tool_names

    def test_graceful_degradation_when_specialist_fails(self):
        """Should still return other specialists when one fails."""
        with patch(
            "src.services.agents._load_weather_tools", return_value=[]
        ):
            tools, availability = build_orchestrator_tools("gpt-4")
            assert availability["weather"] is False
            assert availability["memory"] is True
            tool_names = [t.name for t in tools]
            assert "ask_weather_agent" not in tool_names
            assert "ask_memory_agent" in tool_names


class TestBuildOrchestratorInstructions:
    """Tests for build_orchestrator_instructions function."""

    def test_base_prompt_always_present(self):
        """Orchestrator base prompt should always be included."""
        instructions = build_orchestrator_instructions(
            is_onboarded=None, availability={}
        )
        assert "personal assistant" in instructions
        assert "specialist agents" in instructions

    def test_onboarding_prompt_for_new_user(self):
        """New users get onboarding prompt."""
        instructions = build_orchestrator_instructions(
            is_onboarded=False, availability={}
        )
        assert "meeting this user for the first time" in instructions
        assert "NEVER use generic chatbot phrases" in instructions
        assert "have the tea ready" not in instructions

    def test_proactive_prompt_for_returning_user(self):
        """Returning users get proactive greeting prompt."""
        instructions = build_orchestrator_instructions(
            is_onboarded=True, availability={}
        )
        assert "have the tea ready" in instructions
        assert "meeting this user for the first time" not in instructions

    def test_no_personality_prompt_when_none(self):
        """No personality prompt when is_onboarded is None."""
        instructions = build_orchestrator_instructions(
            is_onboarded=None, availability={}
        )
        assert "meeting this user for the first time" not in instructions
        assert "have the tea ready" not in instructions

    def test_routing_hints_for_available_specialists(self):
        """Available specialists should have routing hints in instructions."""
        availability = {
            "memory": True,
            "knowledge": True,
            "weather": True,
            "proactive": False,
            "notification": False,
        }
        instructions = build_orchestrator_instructions(
            is_onboarded=None, availability=availability
        )
        assert "ask_memory_agent" in instructions
        assert "ask_knowledge_agent" in instructions
        assert "ask_weather_agent" in instructions
        assert "ask_proactive_agent" not in instructions
        assert "ask_notification_agent" not in instructions

    def test_no_routing_hints_when_no_specialists(self):
        """No routing section when no specialists are available."""
        instructions = build_orchestrator_instructions(
            is_onboarded=None, availability={}
        )
        assert "Available specialists" not in instructions
