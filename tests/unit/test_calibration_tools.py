"""Unit tests for adjust_proactiveness and get_user_profile tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.tools.adjust_proactiveness import adjust_proactiveness
from src.tools.get_user_profile import get_user_profile


@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.context = {
        "user_id": str(uuid4()),
        "correlation_id": uuid4(),
        "conversation_id": str(uuid4()),
    }
    return ctx


@pytest.fixture
def mock_ctx_no_user():
    ctx = MagicMock()
    ctx.context = {}
    return ctx


class TestAdjustProactiveness:
    @pytest.mark.asyncio
    async def test_more_increases_level(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.get_or_create_settings.return_value = {
            "global_level": 0.7,
            "suppressed_types": "[]",
        }
        mock_service.update_settings.return_value = {"global_level": 0.9}

        with patch(
            "src.services.proactive_service.ProactiveService",
            return_value=mock_service,
        ):
            result_str = await adjust_proactiveness.on_invoke_tool(
                mock_ctx,
                json.dumps({"direction": "more"}),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["new_level"] == 0.9
        assert result["previous_level"] == 0.7

        # Verify suppressed_types cleared
        call_kwargs = mock_service.update_settings.call_args
        assert "suppressed_types" in call_kwargs[1]

    @pytest.mark.asyncio
    async def test_less_decreases_level(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.get_or_create_settings.return_value = {
            "global_level": 0.7,
            "suppressed_types": "[]",
        }
        mock_service.update_settings.return_value = {"global_level": 0.5}

        with patch(
            "src.services.proactive_service.ProactiveService",
            return_value=mock_service,
        ):
            result_str = await adjust_proactiveness.on_invoke_tool(
                mock_ctx,
                json.dumps({"direction": "less"}),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["new_level"] == 0.5

    @pytest.mark.asyncio
    async def test_clamps_at_max(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.get_or_create_settings.return_value = {
            "global_level": 0.9,
            "suppressed_types": "[]",
        }
        mock_service.update_settings.return_value = {"global_level": 1.0}

        with patch(
            "src.services.proactive_service.ProactiveService",
            return_value=mock_service,
        ):
            result_str = await adjust_proactiveness.on_invoke_tool(
                mock_ctx,
                json.dumps({"direction": "more"}),
            )

        result = json.loads(result_str)
        assert result["new_level"] == 1.0

    @pytest.mark.asyncio
    async def test_clamps_at_min(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.get_or_create_settings.return_value = {
            "global_level": 0.1,
            "suppressed_types": "[]",
        }
        mock_service.update_settings.return_value = {"global_level": 0.0}

        with patch(
            "src.services.proactive_service.ProactiveService",
            return_value=mock_service,
        ):
            result_str = await adjust_proactiveness.on_invoke_tool(
                mock_ctx,
                json.dumps({"direction": "less"}),
            )

        result = json.loads(result_str)
        assert result["new_level"] == 0.0

    @pytest.mark.asyncio
    async def test_invalid_direction(self, mock_ctx):
        result_str = await adjust_proactiveness.on_invoke_tool(
            mock_ctx,
            json.dumps({"direction": "sideways"}),
        )
        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid direction" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_user_id(self, mock_ctx_no_user):
        result_str = await adjust_proactiveness.on_invoke_tool(
            mock_ctx_no_user,
            json.dumps({"direction": "more"}),
        )
        result = json.loads(result_str)
        assert result["success"] is False
        assert "user_id" in result["message"]


class TestGetUserProfile:
    @pytest.mark.asyncio
    async def test_returns_profile(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.get_user_profile.return_value = {
            "facts": [{"content": "Software engineer", "type": "fact", "confidence": 0.95}],
            "preferences": [{"content": "Dark mode", "type": "preference", "confidence": 0.9}],
            "patterns": [{"description": "Asks about weather", "occurrence_count": 5, "acted_on": False}],
            "key_relationships": [{"entity": "Sarah", "relationship": "WORKS_WITH", "mentions": 8}],
            "proactiveness": {"global_level": 0.7, "engaged_categories": [], "suppressed_categories": "[]"},
        }

        with patch(
            "src.services.proactive_service.ProactiveService",
            return_value=mock_service,
        ):
            result_str = await get_user_profile.on_invoke_tool(
                mock_ctx,
                json.dumps({}),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert len(result["facts"]) == 1
        assert len(result["preferences"]) == 1
        assert len(result["patterns"]) == 1

    @pytest.mark.asyncio
    async def test_missing_user_id(self, mock_ctx_no_user):
        result_str = await get_user_profile.on_invoke_tool(
            mock_ctx_no_user,
            json.dumps({}),
        )
        result = json.loads(result_str)
        assert result["success"] is False
        assert "user_id" in result["message"]

    @pytest.mark.asyncio
    async def test_service_error_handled(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.get_user_profile.side_effect = Exception("DB error")

        with patch(
            "src.services.proactive_service.ProactiveService",
            return_value=mock_service,
        ):
            result_str = await get_user_profile.on_invoke_tool(
                mock_ctx,
                json.dumps({}),
            )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Failed to retrieve" in result["message"]
