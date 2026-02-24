"""Validate bundled prompt defaults match the original hardcoded constants."""

import pytest

from src.prompts.defaults import PROMPT_DEFAULTS, PROMPT_NAME_MAP


EXPECTED_PROMPT_NAMES = [
    "orchestrator-base",
    "onboarding",
    "proactive-greeting",
    "memory",
    "memory-write",
    "weather",
    "knowledge-graph",
    "calibration",
    "schedule",
    "observation",
    "notification",
]


class TestPromptDefaults:
    """Tests for PROMPT_DEFAULTS dict."""

    def test_all_11_prompt_names_exist(self):
        for name in EXPECTED_PROMPT_NAMES:
            assert name in PROMPT_DEFAULTS, f"Missing prompt: {name}"

    def test_exactly_11_prompts(self):
        assert len(PROMPT_DEFAULTS) == 11

    def test_all_values_are_non_empty_strings(self):
        for name, text in PROMPT_DEFAULTS.items():
            assert isinstance(text, str), f"{name} is not a string"
            assert len(text.strip()) > 0, f"{name} is empty"


class TestPromptNameMap:
    """Tests for PROMPT_NAME_MAP backward-compat mapping."""

    def test_covers_all_11_constants(self):
        assert len(PROMPT_NAME_MAP) == 11

    def test_all_map_values_are_valid_registry_names(self):
        for const_name, registry_name in PROMPT_NAME_MAP.items():
            assert registry_name in PROMPT_DEFAULTS, (
                f"{const_name} maps to unknown registry name: {registry_name}"
            )

    def test_all_registry_names_are_mapped(self):
        mapped_names = set(PROMPT_NAME_MAP.values())
        for name in EXPECTED_PROMPT_NAMES:
            assert name in mapped_names, f"Registry name {name} has no constant mapping"


class TestBackwardCompatReExports:
    """Verify chat_service.py re-exports match bundled defaults (backward compat)."""

    def test_orchestrator_base_reexport(self):
        from src.services.chat_service import ORCHESTRATOR_BASE_PROMPT
        assert PROMPT_DEFAULTS["orchestrator-base"] == ORCHESTRATOR_BASE_PROMPT

    def test_onboarding_reexport(self):
        from src.services.chat_service import ONBOARDING_SYSTEM_PROMPT
        assert PROMPT_DEFAULTS["onboarding"] == ONBOARDING_SYSTEM_PROMPT

    def test_proactive_greeting_reexport(self):
        from src.services.chat_service import PROACTIVE_GREETING_PROMPT
        assert PROMPT_DEFAULTS["proactive-greeting"] == PROACTIVE_GREETING_PROMPT

    def test_memory_reexport(self):
        from src.services.chat_service import MEMORY_SYSTEM_PROMPT
        assert PROMPT_DEFAULTS["memory"] == MEMORY_SYSTEM_PROMPT

    def test_memory_write_reexport(self):
        from src.services.chat_service import MEMORY_WRITE_SYSTEM_PROMPT
        assert PROMPT_DEFAULTS["memory-write"] == MEMORY_WRITE_SYSTEM_PROMPT

    def test_weather_reexport(self):
        from src.services.chat_service import WEATHER_SYSTEM_PROMPT
        assert PROMPT_DEFAULTS["weather"] == WEATHER_SYSTEM_PROMPT

    def test_knowledge_graph_reexport(self):
        from src.services.chat_service import GRAPH_SYSTEM_PROMPT
        assert PROMPT_DEFAULTS["knowledge-graph"] == GRAPH_SYSTEM_PROMPT

    def test_calibration_reexport(self):
        from src.services.chat_service import CALIBRATION_SYSTEM_PROMPT
        assert PROMPT_DEFAULTS["calibration"] == CALIBRATION_SYSTEM_PROMPT

    def test_schedule_reexport(self):
        from src.services.chat_service import SCHEDULE_SYSTEM_PROMPT
        assert PROMPT_DEFAULTS["schedule"] == SCHEDULE_SYSTEM_PROMPT

    def test_observation_reexport(self):
        from src.services.chat_service import OBSERVATION_SYSTEM_PROMPT
        assert PROMPT_DEFAULTS["observation"] == OBSERVATION_SYSTEM_PROMPT

    def test_notification_reexport(self):
        from src.services.chat_service import NOTIFICATION_SYSTEM_PROMPT
        assert PROMPT_DEFAULTS["notification"] == NOTIFICATION_SYSTEM_PROMPT
