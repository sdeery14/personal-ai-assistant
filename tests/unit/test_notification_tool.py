"""Unit tests for send_notification tool (T014).

Tests tool validation, rate limiting, and service integration
following the established on_invoke_tool pattern.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestSendNotificationTool:
    """Tests for send_notification agent tool."""

    def _make_ctx(self, user_id="test-user", correlation_id=None, conversation_id=None):
        """Create a mock RunContextWrapper."""
        ctx = MagicMock()
        ctx.context = {
            "user_id": user_id,
            "correlation_id": correlation_id or uuid4(),
            "conversation_id": conversation_id or str(uuid4()),
        }
        return ctx

    @pytest.mark.asyncio
    async def test_successful_notification_creation(self):
        """Test that valid input creates a notification and returns success."""
        mock_service = MagicMock()
        mock_service.check_rate_limit = AsyncMock(return_value=True)
        mock_notification = MagicMock()
        mock_notification.id = uuid4()
        mock_service.create_notification = AsyncMock(return_value=mock_notification)

        with patch("src.services.notification_service.NotificationService", return_value=mock_service):
            from src.tools.send_notification import send_notification_tool

            ctx = self._make_ctx()
            result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
                "message": "Don't forget your meeting at 3pm",
                "type": "reminder",
            }))

            result = json.loads(result_str)
            assert result["success"] is True
            assert result["action"] == "notification_created"
            assert "notification_id" in result
            assert result["type"] == "reminder"
            mock_service.create_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_default_type_is_info(self):
        """Test that omitting type defaults to info."""
        mock_service = MagicMock()
        mock_service.check_rate_limit = AsyncMock(return_value=True)
        mock_notification = MagicMock()
        mock_notification.id = uuid4()
        mock_service.create_notification = AsyncMock(return_value=mock_notification)

        with patch("src.services.notification_service.NotificationService", return_value=mock_service):
            from src.tools.send_notification import send_notification_tool

            ctx = self._make_ctx()
            result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
                "message": "Here's some useful information",
            }))

            result = json.loads(result_str)
            assert result["success"] is True
            assert result["type"] == "info"

    @pytest.mark.asyncio
    async def test_empty_message_returns_validation_error(self):
        """Test that empty message returns validation error."""
        from src.tools.send_notification import send_notification_tool

        ctx = self._make_ctx()
        result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
            "message": "",
            "type": "info",
        }))

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "validation_error"

    @pytest.mark.asyncio
    async def test_whitespace_only_message_returns_validation_error(self):
        """Test that whitespace-only message returns validation error."""
        from src.tools.send_notification import send_notification_tool

        ctx = self._make_ctx()
        result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
            "message": "   ",
            "type": "info",
        }))

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "validation_error"

    @pytest.mark.asyncio
    async def test_message_over_500_chars_returns_validation_error(self):
        """Test that message exceeding 500 characters returns validation error."""
        from src.tools.send_notification import send_notification_tool

        ctx = self._make_ctx()
        result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
            "message": "x" * 501,
            "type": "info",
        }))

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "validation_error"
        assert "500" in result["message"]

    @pytest.mark.asyncio
    async def test_invalid_type_returns_validation_error(self):
        """Test that invalid notification type returns validation error."""
        from src.tools.send_notification import send_notification_tool

        ctx = self._make_ctx()
        result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
            "message": "Test message",
            "type": "urgent",
        }))

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "validation_error"
        assert "urgent" in result["message"]

    @pytest.mark.asyncio
    async def test_missing_user_id_returns_error(self):
        """Test that missing user_id in context returns error."""
        from src.tools.send_notification import send_notification_tool

        ctx = self._make_ctx(user_id=None)
        result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
            "message": "Test message",
            "type": "info",
        }))

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "error"
        assert "user_id" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_returns_rate_limited(self):
        """Test that exceeding rate limit returns rate_limited response."""
        mock_service = MagicMock()
        mock_service.check_rate_limit = AsyncMock(return_value=False)

        with patch("src.services.notification_service.NotificationService", return_value=mock_service):
            from src.tools.send_notification import send_notification_tool

            ctx = self._make_ctx()
            result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
                "message": "Test message",
                "type": "info",
            }))

            result = json.loads(result_str)
            assert result["success"] is False
            assert result["action"] == "rate_limited"

    @pytest.mark.asyncio
    async def test_service_exception_returns_error(self):
        """Test that service exception returns error response."""
        mock_service = MagicMock()
        mock_service.check_rate_limit = AsyncMock(return_value=True)
        mock_service.create_notification = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        with patch("src.services.notification_service.NotificationService", return_value=mock_service):
            from src.tools.send_notification import send_notification_tool

            ctx = self._make_ctx()
            result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
                "message": "Test message",
                "type": "info",
            }))

            result = json.loads(result_str)
            assert result["success"] is False
            assert result["action"] == "error"
            assert "Database connection failed" in result["message"]

    @pytest.mark.asyncio
    async def test_response_is_valid_json(self):
        """Test that all responses are valid JSON with required fields."""
        from src.tools.send_notification import send_notification_tool

        ctx = self._make_ctx(user_id=None)
        result_str = await send_notification_tool.on_invoke_tool(ctx, json.dumps({
            "message": "Test",
            "type": "info",
        }))

        result = json.loads(result_str)
        assert "success" in result
        assert "action" in result
        assert "message" in result
