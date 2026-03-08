"""Unit tests for prompt_service — seed, register, load, version tracking."""

from unittest.mock import MagicMock, patch

import pytest

from src.prompts.defaults import PROMPT_DEFAULTS
from src.services.prompt_service import PromptVersionInfo


# ---------------------------------------------------------------------------
# US1: seed_prompts tests (T006)
# ---------------------------------------------------------------------------


class TestSeedPrompts:
    """Tests for seed_prompts() — seeding registry from bundled defaults."""

    @patch("src.services.prompt_service.mlflow")
    def test_seeds_all_11_when_empty(self, mock_mlflow):
        """When no prompts exist in registry, all 11 should be seeded."""
        from src.services.prompt_service import seed_prompts

        # load_prompt returns None for all (nothing exists)
        mock_mlflow.genai.load_prompt.return_value = None
        # register_prompt returns a mock with version=1
        mock_version = MagicMock()
        mock_version.version = 1
        mock_mlflow.genai.register_prompt.return_value = mock_version

        result = seed_prompts()

        assert len(result) == 11
        assert mock_mlflow.genai.register_prompt.call_count == 11
        assert mock_mlflow.genai.set_prompt_alias.call_count == 11
        for name in PROMPT_DEFAULTS:
            assert name in result
            assert result[name] == 1

    @patch("src.services.prompt_service.mlflow")
    def test_skips_existing_prompts(self, mock_mlflow):
        """When prompts already exist, they should be skipped."""
        from src.services.prompt_service import seed_prompts

        # load_prompt returns a mock PromptVersion (exists)
        mock_existing = MagicMock()
        mock_existing.version = 1
        mock_mlflow.genai.load_prompt.return_value = mock_existing

        result = seed_prompts()

        assert len(result) == 0
        mock_mlflow.genai.register_prompt.assert_not_called()
        mock_mlflow.genai.set_prompt_alias.assert_not_called()

    @patch("src.services.prompt_service.mlflow")
    def test_handles_mlflow_connection_failure(self, mock_mlflow):
        """On MLflow connection error, returns empty dict gracefully."""
        from src.services.prompt_service import seed_prompts

        mock_mlflow.genai.load_prompt.side_effect = ConnectionError("MLflow down")

        result = seed_prompts()

        assert result == {}

    @patch("src.services.prompt_service.mlflow")
    def test_idempotent_on_repeated_calls(self, mock_mlflow):
        """Calling seed_prompts twice yields same result."""
        from src.services.prompt_service import seed_prompts

        mock_existing = MagicMock()
        mock_existing.version = 1
        mock_mlflow.genai.load_prompt.return_value = mock_existing

        result1 = seed_prompts()
        result2 = seed_prompts()

        assert result1 == result2 == {}


# ---------------------------------------------------------------------------
# US1: register_prompt + get_active_prompt_versions tests (T007)
# ---------------------------------------------------------------------------


class TestRegisterPrompt:
    """Tests for register_prompt() — creating new prompt versions."""

    @patch("src.services.prompt_service.mlflow")
    def test_returns_new_version_number(self, mock_mlflow):
        """register_prompt should return the new version number."""
        from src.services.prompt_service import register_prompt

        mock_version = MagicMock()
        mock_version.version = 3
        mock_mlflow.genai.register_prompt.return_value = mock_version

        result = register_prompt(
            name="orchestrator-base",
            template="Updated prompt text",
            commit_message="Test update",
        )

        assert result == 3
        mock_mlflow.genai.register_prompt.assert_called_once_with(
            name="orchestrator-base",
            template="Updated prompt text",
            commit_message="Test update",
            model_config=None,
        )

    @patch("src.services.prompt_service.mlflow")
    def test_passes_model_config_through(self, mock_mlflow):
        """register_prompt should pass model_config to MLflow."""
        from src.services.prompt_service import register_prompt

        mock_version = MagicMock()
        mock_version.version = 2
        mock_mlflow.genai.register_prompt.return_value = mock_version

        config = {"temperature": 0.7, "max_tokens": 500}
        result = register_prompt(
            name="weather",
            template="Weather prompt",
            commit_message="Add config",
            model_config=config,
        )

        assert result == 2
        mock_mlflow.genai.register_prompt.assert_called_once_with(
            name="weather",
            template="Weather prompt",
            commit_message="Add config",
            model_config=config,
        )


class TestGetActivePromptVersions:
    """Tests for get_active_prompt_versions() — version tracking dict."""

    def test_returns_dict_of_loaded_versions(self):
        """get_active_prompt_versions should return a copy of the active versions dict."""
        from src.services.prompt_service import (
            _active_versions,
            get_active_prompt_versions,
        )

        # Manually set some versions for testing
        _active_versions.clear()
        _active_versions["orchestrator-base"] = 3
        _active_versions["memory"] = 1

        result = get_active_prompt_versions()

        assert result == {"orchestrator-base": 3, "memory": 1}
        # Verify it's a copy (modifying result doesn't affect internal state)
        result["orchestrator-base"] = 999
        assert _active_versions["orchestrator-base"] == 3

        # Cleanup
        _active_versions.clear()


# ---------------------------------------------------------------------------
# US2: load_prompt tests (T012)
# ---------------------------------------------------------------------------


class TestLoadPrompt:
    """Tests for load_prompt() — loading from registry with fallback."""

    @patch("src.services.prompt_service.mlflow")
    def test_returns_template_text_on_success(self, mock_mlflow):
        """load_prompt should return template text from registry."""
        from src.services.prompt_service import load_prompt

        mock_pv = MagicMock()
        mock_pv.template = "Registry prompt text"
        mock_pv.version = 2
        mock_mlflow.genai.load_prompt.return_value = mock_pv

        result = load_prompt("orchestrator-base")

        assert result == "Registry prompt text"

    @patch("src.services.prompt_service.mlflow")
    def test_returns_bundled_default_on_mlflow_exception(self, mock_mlflow):
        """load_prompt should fall back to bundled default on MlflowException."""
        from src.services.prompt_service import load_prompt

        mock_mlflow.genai.load_prompt.side_effect = Exception("MlflowException")

        result = load_prompt("memory")

        assert result == PROMPT_DEFAULTS["memory"]

    @patch("src.services.prompt_service.mlflow")
    def test_returns_bundled_default_on_connection_error(self, mock_mlflow):
        """load_prompt should fall back to bundled default on connection error."""
        from src.services.prompt_service import load_prompt

        mock_mlflow.genai.load_prompt.side_effect = ConnectionError("MLflow down")

        result = load_prompt("weather")

        assert result == PROMPT_DEFAULTS["weather"]

    @patch("src.services.prompt_service.settings")
    @patch("src.services.prompt_service.mlflow")
    def test_passes_cache_ttl_from_settings(self, mock_mlflow, mock_settings):
        """load_prompt should pass cache_ttl_seconds from settings."""
        from src.services.prompt_service import load_prompt

        mock_settings.prompt_cache_ttl_seconds = 600
        mock_settings.prompt_alias = "production"
        mock_pv = MagicMock()
        mock_pv.template = "Cached prompt"
        mock_pv.version = 1
        mock_mlflow.genai.load_prompt.return_value = mock_pv

        load_prompt("memory")

        mock_mlflow.genai.load_prompt.assert_called_once_with(
            "prompts:/memory@production",
            cache_ttl_seconds=600,
        )

    @patch("src.services.prompt_service.settings")
    @patch("src.services.prompt_service.mlflow")
    def test_constructs_correct_uri_format(self, mock_mlflow, mock_settings):
        """load_prompt should use prompts:/{name}@{alias} URI format."""
        from src.services.prompt_service import load_prompt

        mock_settings.prompt_cache_ttl_seconds = 300
        mock_settings.prompt_alias = "experiment"
        mock_pv = MagicMock()
        mock_pv.template = "Experiment prompt"
        mock_pv.version = 3
        mock_mlflow.genai.load_prompt.return_value = mock_pv

        load_prompt("orchestrator-base")

        mock_mlflow.genai.load_prompt.assert_called_once_with(
            "prompts:/orchestrator-base@experiment",
            cache_ttl_seconds=300,
        )

    @patch("src.services.prompt_service.settings")
    @patch("src.services.prompt_service.mlflow")
    def test_alias_override(self, mock_mlflow, mock_settings):
        """load_prompt with explicit alias should override settings default."""
        from src.services.prompt_service import load_prompt

        mock_settings.prompt_cache_ttl_seconds = 300
        mock_settings.prompt_alias = "production"
        mock_pv = MagicMock()
        mock_pv.template = "Staging prompt"
        mock_pv.version = 5
        mock_mlflow.genai.load_prompt.return_value = mock_pv

        load_prompt("memory", alias="staging")

        mock_mlflow.genai.load_prompt.assert_called_once_with(
            "prompts:/memory@staging",
            cache_ttl_seconds=300,
        )


# ---------------------------------------------------------------------------
# US2: load_prompt_version tests (T013)
# ---------------------------------------------------------------------------


class TestLoadPromptVersion:
    """Tests for load_prompt_version() — loading with full metadata."""

    @patch("src.services.prompt_service.settings")
    @patch("src.services.prompt_service.mlflow")
    def test_returns_prompt_version_info_on_success(self, mock_mlflow, mock_settings):
        """load_prompt_version should return PromptVersionInfo with correct fields."""
        from src.services.prompt_service import load_prompt_version

        mock_settings.prompt_cache_ttl_seconds = 300
        mock_settings.prompt_alias = "production"
        mock_pv = MagicMock()
        mock_pv.template = "Loaded prompt text"
        mock_pv.version = 3
        mock_pv.model_config = {"temperature": 0.7}
        mock_mlflow.genai.load_prompt.return_value = mock_pv

        result = load_prompt_version("orchestrator-base")

        assert isinstance(result, PromptVersionInfo)
        assert result.name == "orchestrator-base"
        assert result.version == 3
        assert result.alias == "production"
        assert result.template == "Loaded prompt text"
        assert result.model_config == {"temperature": 0.7}
        assert result.is_fallback is False

    @patch("src.services.prompt_service.mlflow")
    def test_is_fallback_true_on_failure(self, mock_mlflow):
        """load_prompt_version should return fallback PromptVersionInfo on failure."""
        from src.services.prompt_service import load_prompt_version

        mock_mlflow.genai.load_prompt.side_effect = ConnectionError("MLflow down")

        result = load_prompt_version("memory")

        assert isinstance(result, PromptVersionInfo)
        assert result.name == "memory"
        assert result.version == 0
        assert result.template == PROMPT_DEFAULTS["memory"]
        assert result.is_fallback is True
        assert result.model_config is None


# ---------------------------------------------------------------------------
# US3: set_alias tests (T021)
# ---------------------------------------------------------------------------


class TestSetAlias:
    """Tests for set_alias() — pointing aliases to specific versions."""

    @patch("src.services.prompt_service.mlflow")
    def test_calls_mlflow_with_correct_args(self, mock_mlflow):
        """set_alias should call MLflow with correct name, alias, version."""
        from src.services.prompt_service import set_alias

        set_alias("orchestrator-base", alias="experiment", version=3)

        mock_mlflow.genai.set_prompt_alias.assert_called_once_with(
            name="orchestrator-base",
            alias="experiment",
            version=3,
        )

    @patch("src.services.prompt_service.mlflow")
    def test_alias_based_loading_returns_different_content(self, mock_mlflow):
        """After re-pointing alias, load should return different content."""
        from src.services.prompt_service import load_prompt

        # First load returns v1 content
        mock_pv1 = MagicMock()
        mock_pv1.template = "Version 1 content"
        mock_pv1.version = 1

        # Second load returns v2 content
        mock_pv2 = MagicMock()
        mock_pv2.template = "Version 2 content"
        mock_pv2.version = 2

        mock_mlflow.genai.load_prompt.side_effect = [mock_pv1, mock_pv2]

        result1 = load_prompt("orchestrator-base")
        result2 = load_prompt("orchestrator-base")

        assert result1 == "Version 1 content"
        assert result2 == "Version 2 content"


# ---------------------------------------------------------------------------
# US4: model_config tests (T023)
# ---------------------------------------------------------------------------


class TestModelConfig:
    """Tests for model_config passthrough in register and load."""

    @patch("src.services.prompt_service.mlflow")
    def test_register_passes_model_config(self, mock_mlflow):
        """register_prompt should pass model_config dict through to MLflow."""
        from src.services.prompt_service import register_prompt

        mock_version = MagicMock()
        mock_version.version = 1
        mock_mlflow.genai.register_prompt.return_value = mock_version

        config = {"temperature": 0.8, "max_tokens": 1000}
        register_prompt(
            name="weather",
            template="Test",
            commit_message="With config",
            model_config=config,
        )

        mock_mlflow.genai.register_prompt.assert_called_once_with(
            name="weather",
            template="Test",
            commit_message="With config",
            model_config=config,
        )

    @patch("src.services.prompt_service.settings")
    @patch("src.services.prompt_service.mlflow")
    def test_load_prompt_version_returns_model_config(self, mock_mlflow, mock_settings):
        """load_prompt_version should return model_config from PromptVersion."""
        from src.services.prompt_service import load_prompt_version

        mock_settings.prompt_cache_ttl_seconds = 300
        mock_settings.prompt_alias = "production"
        mock_pv = MagicMock()
        mock_pv.template = "Prompt with config"
        mock_pv.version = 2
        mock_pv.model_config = {"temperature": 0.5, "top_p": 0.9}
        mock_mlflow.genai.load_prompt.return_value = mock_pv

        result = load_prompt_version("weather")

        assert result.model_config == {"temperature": 0.5, "top_p": 0.9}

    @patch("src.services.prompt_service.mlflow")
    def test_seed_includes_default_model_config(self, mock_mlflow):
        """seed_prompts should include default model_config from settings."""
        from src.services.prompt_service import seed_prompts

        mock_mlflow.genai.load_prompt.return_value = None
        mock_version = MagicMock()
        mock_version.version = 1
        mock_mlflow.genai.register_prompt.return_value = mock_version

        result = seed_prompts()

        assert len(result) == 11
        # Verify register_prompt was called with model_config containing model and max_tokens
        for call in mock_mlflow.genai.register_prompt.call_args_list:
            cfg = call.kwargs["model_config"]
            assert "model" in cfg
            assert "max_tokens" in cfg
