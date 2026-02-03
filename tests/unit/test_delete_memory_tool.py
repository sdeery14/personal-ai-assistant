"""Unit tests for delete_memory tool logic."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestDeleteMemorySearchMode:
    """Tests for search mode (confirm=False)."""

    def _make_ctx(self, user_id="test-user"):
        """Create mock RunContextWrapper."""
        ctx = MagicMock()
        ctx.context = {
            "user_id": user_id,
            "correlation_id": uuid4(),
        }
        return ctx

    @pytest.mark.asyncio
    async def test_search_mode_returns_candidates(self):
        """Test that search mode returns matching memories."""
        mock_candidates = [
            {"id": str(uuid4()), "content": "User lives in Portland", "type": "fact", "relevance": 0.8},
        ]

        with patch("src.tools.delete_memory.MemoryWriteService") as MockService:
            mock_service = MockService.return_value
            mock_service.search_memories = AsyncMock(return_value=mock_candidates)

            from src.tools.delete_memory import delete_memory_tool
            ctx = self._make_ctx()

            result_str = await delete_memory_tool.on_invoke_tool(ctx, json.dumps({
                "description": "Portland location",
                "confirm": False,
            }))

            result = json.loads(result_str)
            assert result["action"] == "candidates_found"
            assert len(result["candidates"]) == 1
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_search_mode_no_matches(self):
        """Test search mode when no memories match."""
        with patch("src.tools.delete_memory.MemoryWriteService") as MockService:
            mock_service = MockService.return_value
            mock_service.search_memories = AsyncMock(return_value=[])

            from src.tools.delete_memory import delete_memory_tool
            ctx = self._make_ctx()

            result_str = await delete_memory_tool.on_invoke_tool(ctx, json.dumps({
                "description": "nonexistent memory",
                "confirm": False,
            }))

            result = json.loads(result_str)
            assert result["action"] == "not_found"
            assert result["success"] is False


class TestDeleteMemoryConfirmMode:
    """Tests for confirm mode (confirm=True)."""

    def _make_ctx(self, user_id="test-user"):
        """Create mock RunContextWrapper."""
        ctx = MagicMock()
        ctx.context = {
            "user_id": user_id,
            "correlation_id": uuid4(),
        }
        return ctx

    @pytest.mark.asyncio
    async def test_confirm_mode_schedules_deletion(self):
        """Test that confirm mode schedules async deletion."""
        with patch("src.tools.delete_memory.MemoryWriteService"):
            with patch("src.tools.delete_memory.schedule_write") as mock_schedule:
                mock_schedule.return_value = MagicMock()

                from src.tools.delete_memory import delete_memory_tool
                ctx = self._make_ctx()

                result_str = await delete_memory_tool.on_invoke_tool(ctx, json.dumps({
                    "description": "Portland location",
                    "confirm": True,
                }))

                result = json.loads(result_str)
                assert result["action"] == "deletion_queued"
                assert result["success"] is True
                mock_schedule.assert_called_once()


class TestDeleteMemoryValidation:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_missing_user_id_returns_error(self):
        """Test that missing user_id returns error."""
        from src.tools.delete_memory import delete_memory_tool
        ctx = MagicMock()
        ctx.context = {"user_id": None, "correlation_id": uuid4()}

        result_str = await delete_memory_tool.on_invoke_tool(ctx, json.dumps({
            "description": "some memory",
        }))

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "error"
        assert "user_id" in result["message"]

    @pytest.mark.asyncio
    async def test_response_is_valid_json(self):
        """Test all responses are valid JSON."""
        from src.tools.delete_memory import delete_memory_tool
        ctx = MagicMock()
        ctx.context = {"user_id": "test-user", "correlation_id": uuid4()}

        with patch("src.tools.delete_memory.MemoryWriteService") as MockService:
            mock_service = MockService.return_value
            mock_service.search_memories = AsyncMock(return_value=[])

            result_str = await delete_memory_tool.on_invoke_tool(ctx, json.dumps({
                "description": "test",
            }))

            result = json.loads(result_str)
            assert "success" in result
            assert "action" in result
            assert "message" in result
