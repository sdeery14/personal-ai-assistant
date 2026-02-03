"""Unit tests for save_memory tool logic."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestSaveMemoryConfidenceGating:
    """Tests for confidence-based gating in save_memory tool."""

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
    async def test_high_confidence_queued(self):
        """Test that high confidence (>=0.7) results in queued write."""
        with patch("src.tools.save_memory.MemoryWriteService") as MockService:
            with patch("src.tools.save_memory.schedule_write") as mock_schedule:
                mock_schedule.return_value = MagicMock()

                # Import and get the wrapped function
                from src.tools.save_memory import save_memory_tool
                # Call the underlying function directly
                ctx = self._make_ctx()
                result_str = await save_memory_tool.on_invoke_tool(ctx, json.dumps({
                    "content": "User likes Python",
                    "memory_type": "preference",
                    "confidence": 0.85,
                    "importance": 0.6,
                }))

                result = json.loads(result_str)
                assert result["action"] == "queued"
                assert result["success"] is True
                mock_schedule.assert_called_once()

    @pytest.mark.asyncio
    async def test_medium_confidence_needs_confirmation(self):
        """Test that medium confidence (0.5-0.7) returns confirm_needed."""
        from src.tools.save_memory import save_memory_tool
        ctx = self._make_ctx()

        result_str = await save_memory_tool.on_invoke_tool(ctx, json.dumps({
            "content": "User might like TypeScript",
            "memory_type": "preference",
            "confidence": 0.6,
        }))

        result = json.loads(result_str)
        assert result["action"] == "confirm_needed"
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_low_confidence_discarded(self):
        """Test that low confidence (<0.5) discards the memory."""
        from src.tools.save_memory import save_memory_tool
        ctx = self._make_ctx()

        result_str = await save_memory_tool.on_invoke_tool(ctx, json.dumps({
            "content": "User possibly interested in Haskell",
            "memory_type": "preference",
            "confidence": 0.3,
        }))

        result = json.loads(result_str)
        assert result["action"] == "discarded"
        assert result["success"] is False


class TestSaveMemoryValidation:
    """Tests for input validation."""

    def _make_ctx(self, user_id=None):
        """Create mock context."""
        ctx = MagicMock()
        ctx.context = {
            "user_id": user_id,
            "correlation_id": uuid4(),
            "conversation_id": str(uuid4()),
        }
        return ctx

    @pytest.mark.asyncio
    async def test_missing_user_id_returns_error(self):
        """Test that missing user_id returns error."""
        from src.tools.save_memory import save_memory_tool
        ctx = self._make_ctx(user_id=None)

        result_str = await save_memory_tool.on_invoke_tool(ctx, json.dumps({
            "content": "Some content",
            "memory_type": "fact",
        }))

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "error"
        assert "user_id" in result["message"]

    @pytest.mark.asyncio
    async def test_invalid_memory_type_returns_error(self):
        """Test that invalid memory type returns error."""
        from src.tools.save_memory import save_memory_tool
        ctx = self._make_ctx(user_id="test-user")

        result_str = await save_memory_tool.on_invoke_tool(ctx, json.dumps({
            "content": "Some content",
            "memory_type": "invalid_type",
        }))

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "error"
        assert "Invalid memory type" in result["message"]

    @pytest.mark.asyncio
    async def test_episode_type_not_allowed(self):
        """Test that episode type is not allowed via save_memory_tool."""
        from src.tools.save_memory import save_memory_tool
        ctx = self._make_ctx(user_id="test-user")

        result_str = await save_memory_tool.on_invoke_tool(ctx, json.dumps({
            "content": "Episode content",
            "memory_type": "episode",
        }))

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "error"


class TestSaveMemoryResponseFormat:
    """Tests for response format consistency."""

    @pytest.mark.asyncio
    async def test_response_is_valid_json(self):
        """Test that all responses are valid JSON."""
        from src.tools.save_memory import save_memory_tool
        ctx = MagicMock()
        ctx.context = {"user_id": "test-user", "correlation_id": uuid4(), "conversation_id": str(uuid4())}

        with patch("src.tools.save_memory.MemoryWriteService"):
            with patch("src.tools.save_memory.schedule_write"):
                result_str = await save_memory_tool.on_invoke_tool(ctx, json.dumps({
                    "content": "Test",
                    "memory_type": "fact",
                    "confidence": 0.9,
                }))

                result = json.loads(result_str)
                assert "success" in result
                assert "action" in result
                assert "message" in result
