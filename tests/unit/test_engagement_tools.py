"""Unit tests for record_engagement tool."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.tools.record_engagement import record_engagement


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


class TestRecordEngagementTool:
    @pytest.mark.asyncio
    async def test_successful_engaged_recording(self, mock_ctx):
        mock_service = AsyncMock()
        event_id = str(uuid4())
        mock_service.record_event.return_value = {
            "event_id": event_id,
            "suggestion_type": "weather_briefing",
            "action": "engaged",
        }

        with patch(
            "src.services.engagement_service.EngagementService",
            return_value=mock_service,
        ):
            result_str = await record_engagement.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "suggestion_type": "weather_briefing",
                    "action": "engaged",
                    "source": "conversation",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["action"] == "engaged"
        assert result["event_id"] == event_id

        mock_service.record_event.assert_called_once_with(
            user_id=mock_ctx.context["user_id"],
            suggestion_type="weather_briefing",
            action="engaged",
            source="conversation",
        )

    @pytest.mark.asyncio
    async def test_successful_dismissed_recording(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.record_event.return_value = {
            "event_id": str(uuid4()),
            "suggestion_type": "meeting_prep",
            "action": "dismissed",
        }

        with patch(
            "src.services.engagement_service.EngagementService",
            return_value=mock_service,
        ):
            result_str = await record_engagement.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "suggestion_type": "meeting_prep",
                    "action": "dismissed",
                    "source": "notification",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["action"] == "dismissed"

    @pytest.mark.asyncio
    async def test_missing_user_id(self, mock_ctx_no_user):
        result_str = await record_engagement.on_invoke_tool(
            mock_ctx_no_user,
            json.dumps({
                "suggestion_type": "weather_briefing",
                "action": "engaged",
                "source": "conversation",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "user_id" in result["message"]

    @pytest.mark.asyncio
    async def test_invalid_action(self, mock_ctx):
        result_str = await record_engagement.on_invoke_tool(
            mock_ctx,
            json.dumps({
                "suggestion_type": "weather_briefing",
                "action": "ignored",
                "source": "conversation",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid action" in result["message"]

    @pytest.mark.asyncio
    async def test_invalid_source(self, mock_ctx):
        result_str = await record_engagement.on_invoke_tool(
            mock_ctx,
            json.dumps({
                "suggestion_type": "weather_briefing",
                "action": "engaged",
                "source": "email",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid source" in result["message"]

    @pytest.mark.asyncio
    async def test_service_error_handled(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.record_event.side_effect = Exception("DB error")

        with patch(
            "src.services.engagement_service.EngagementService",
            return_value=mock_service,
        ):
            result_str = await record_engagement.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "suggestion_type": "weather_briefing",
                    "action": "engaged",
                    "source": "conversation",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Failed to record engagement" in result["message"]

    @pytest.mark.asyncio
    async def test_schedule_source(self, mock_ctx):
        mock_service = AsyncMock()
        mock_service.record_event.return_value = {
            "event_id": str(uuid4()),
            "suggestion_type": "daily_summary",
            "action": "engaged",
        }

        with patch(
            "src.services.engagement_service.EngagementService",
            return_value=mock_service,
        ):
            result_str = await record_engagement.on_invoke_tool(
                mock_ctx,
                json.dumps({
                    "suggestion_type": "daily_summary",
                    "action": "engaged",
                    "source": "schedule",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
