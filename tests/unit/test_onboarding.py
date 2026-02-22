"""Unit tests for onboarding prompt injection in ChatService."""

from unittest.mock import patch, MagicMock

import pytest

from src.services.chat_service import (
    ChatService,
    ONBOARDING_SYSTEM_PROMPT,
    PROACTIVE_GREETING_PROMPT,
)


@pytest.fixture
def chat_service():
    """Create ChatService with mocked dependencies."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        service = ChatService()
        service._database_available = True
        service._weather_available = False
        service._graph_available = False
        service._notifications_available = False
        # Mock conversation service to avoid database calls
        service._conversation_service = MagicMock()
        return service


class TestOnboardingPromptInjection:
    def test_new_user_gets_onboarding_prompt(self, chat_service):
        """New users (is_onboarded=False) get the onboarding system prompt."""
        agent = chat_service.create_agent(is_onboarded=False)
        assert "meeting this user for the first time" in agent.instructions
        assert ONBOARDING_SYSTEM_PROMPT.strip()[:50] in agent.instructions

    def test_returning_user_gets_proactive_prompt(self, chat_service):
        """Returning users (is_onboarded=True) get the proactive greeting prompt."""
        agent = chat_service.create_agent(is_onboarded=True)
        assert "You know this user already" in agent.instructions
        assert PROACTIVE_GREETING_PROMPT.strip()[:50] in agent.instructions

    def test_new_user_does_not_get_proactive_prompt(self, chat_service):
        """New users should NOT get the proactive greeting prompt."""
        agent = chat_service.create_agent(is_onboarded=False)
        assert "You know this user already" not in agent.instructions

    def test_returning_user_does_not_get_onboarding_prompt(self, chat_service):
        """Returning users should NOT get the onboarding prompt."""
        agent = chat_service.create_agent(is_onboarded=True)
        assert "meeting this user for the first time" not in agent.instructions

    def test_no_onboarding_info_gives_default(self, chat_service):
        """When is_onboarded is None (e.g., anonymous user), neither prompt is injected."""
        agent = chat_service.create_agent(is_onboarded=None)
        assert "meeting this user for the first time" not in agent.instructions
        assert "You know this user already" not in agent.instructions

    def test_memory_prompts_always_present_when_db_available(self, chat_service):
        """Memory prompts should be present regardless of onboarding status."""
        for onboarded_state in [True, False, None]:
            agent = chat_service.create_agent(is_onboarded=onboarded_state)
            assert "save_memory_tool" in agent.instructions

    def test_onboarding_prompt_includes_memory_guidance(self, chat_service):
        """Onboarding prompt should work alongside memory write prompt."""
        agent = chat_service.create_agent(is_onboarded=False)
        # Both onboarding and memory write instructions present
        assert "meeting this user for the first time" in agent.instructions
        assert "save_memory_tool" in agent.instructions


class TestOnboardingBackwardCompatibility:
    def test_create_agent_without_user_id(self, chat_service):
        """create_agent() still works without user_id/is_onboarded for eval framework."""
        agent = chat_service.create_agent()
        assert agent is not None
        assert "helpful assistant" in agent.instructions

    def test_create_agent_with_model_only(self, chat_service):
        """create_agent(model=...) still works as before."""
        agent = chat_service.create_agent(model="gpt-4")
        assert agent is not None
