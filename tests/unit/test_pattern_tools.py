"""Unit tests for record_pattern tool."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.tools.record_pattern import record_pattern


@pytest.fixture
def mock_ctx():
    """Create a mock RunContextWrapper with user context."""
    ctx = MagicMock()
    ctx.context = {
        "user_id": str(uuid4()),
        "correlation_id": uuid4(),
        "conversation_id": str(uuid4()),
    }
    return ctx


@pytest.fixture
def mock_ctx_no_user():
    """Create a mock RunContextWrapper without user_id."""
    ctx = MagicMock()
    ctx.context = {}
    return ctx


class TestRecordPatternTool:
    @pytest.mark.asyncio
    async def test_successful_recording(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.record_or_update_pattern.return_value = {
            "pattern_id": str(uuid4()),
            "occurrence_count": 1,
            "threshold_reached": False,
        }

        with patch(
            "src.services.pattern_service.PatternService",
            return_value=mock_service,
        ):
            result_str = await record_pattern.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "pattern_type": "recurring_query",
                    "description": "Asks about weather",
                    "evidence": "Asked about Seattle weather",
                    "confidence": 0.6,
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["occurrence_count"] == 1
        assert result["threshold_reached"] is False

        mock_service.record_or_update_pattern.assert_called_once_with(
            user_id=mock_ctx.context["user_id"],
            pattern_type="recurring_query",
            description="Asks about weather",
            evidence="Asked about Seattle weather",
            suggested_action=None,
            confidence=0.6,
        )

    @pytest.mark.asyncio
    async def test_with_suggested_action(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.record_or_update_pattern.return_value = {
            "pattern_id": str(uuid4()),
            "occurrence_count": 3,
            "threshold_reached": True,
        }

        with patch(
            "src.services.pattern_service.PatternService",
            return_value=mock_service,
        ):
            result_str = await record_pattern.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "pattern_type": "time_based",
                    "description": "Checks weather every morning",
                    "evidence": "Morning weather request",
                    "suggested_action": "Schedule daily weather at 7am",
                    "confidence": 0.8,
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["threshold_reached"] is True

    @pytest.mark.asyncio
    async def test_duplicate_pattern_update(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.record_or_update_pattern.return_value = {
            "pattern_id": str(uuid4()),
            "occurrence_count": 2,
            "threshold_reached": False,
        }

        with patch(
            "src.services.pattern_service.PatternService",
            return_value=mock_service,
        ):
            result_str = await record_pattern.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "pattern_type": "topic_interest",
                    "description": "Interest in Python",
                    "evidence": "Discussed Python again",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["occurrence_count"] == 2

    @pytest.mark.asyncio
    async def test_missing_user_id(self, mock_ctx_no_user):
        result_str = await record_pattern.on_invoke_tool(
            mock_ctx_no_user,
            json.dumps({
                "pattern_type": "recurring_query",
                "description": "test",
                "evidence": "test",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "error"
        assert "user_id" in result["message"]

    @pytest.mark.asyncio
    async def test_invalid_pattern_type(self, mock_ctx):
        result_str = await record_pattern.on_invoke_tool(
            mock_ctx,
            json.dumps({
                "pattern_type": "invalid_type",
                "description": "test",
                "evidence": "test",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid pattern_type" in result["message"]

    @pytest.mark.asyncio
    async def test_invalid_confidence(self, mock_ctx):
        result_str = await record_pattern.on_invoke_tool(
            mock_ctx,
            json.dumps({
                "pattern_type": "recurring_query",
                "description": "test",
                "evidence": "test",
                "confidence": 1.5,
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Confidence" in result["message"]

    @pytest.mark.asyncio
    async def test_service_error_handled(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.record_or_update_pattern.side_effect = Exception("DB error")

        with patch(
            "src.services.pattern_service.PatternService",
            return_value=mock_service,
        ):
            result_str = await record_pattern.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "pattern_type": "recurring_query",
                    "description": "test",
                    "evidence": "test",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Failed to record pattern" in result["message"]
