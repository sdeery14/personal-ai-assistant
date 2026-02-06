"""Unit tests for the save_entity tool."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.models.graph import EntityType


class TestSaveEntityTool:
    """Tests for save_entity agent tool."""

    def _make_ctx(self, user_id="test-user", conversation_id=None):
        """Create mock run context."""
        ctx = MagicMock()
        ctx.context = {
            "user_id": user_id,
            "correlation_id": uuid4(),
            "conversation_id": conversation_id or str(uuid4()),
        }
        return ctx

    def _make_mock_entity(self, entity_type=EntityType.TOOL, mention_count=1):
        """Create a mock entity."""
        from src.models.graph import Entity

        return Entity(
            id=uuid4(),
            user_id="test-user",
            name="FastAPI",
            canonical_name="fastapi",
            type=entity_type,
            confidence=0.9,
            mention_count=mention_count,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_save_entity_creates_new(self):
        """Test creating a new entity."""
        mock_entity = self._make_mock_entity()

        # Mock at the service module level since the tool uses inline imports
        mock_service = MagicMock()
        mock_service.get_or_create_entity = AsyncMock(
            return_value=(mock_entity, True)
        )

        with patch(
            "src.services.redis_service.check_graph_entity_rate_limit",
            new_callable=AsyncMock,
            return_value=(True, None),
        ), patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.save_entity import save_entity_tool

            ctx = self._make_ctx()
            result_str = await save_entity_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "name": "FastAPI",
                    "entity_type": "tool",
                    "description": "A web framework",
                    "confidence": 0.9,
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["entity_name"] == "FastAPI"
        assert result["entity_type"] == "tool"

    @pytest.mark.asyncio
    async def test_save_entity_returns_existing(self):
        """Test returning existing entity."""
        mock_entity = self._make_mock_entity(mention_count=5)

        mock_service = MagicMock()
        mock_service.get_or_create_entity = AsyncMock(
            return_value=(mock_entity, False)
        )

        with patch(
            "src.services.redis_service.check_graph_entity_rate_limit",
            new_callable=AsyncMock,
            return_value=(True, None),
        ), patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.save_entity import save_entity_tool

            ctx = self._make_ctx()
            result_str = await save_entity_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "name": "FastAPI",
                    "entity_type": "tool",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["action"] == "existing"
        assert "mention #5" in result["message"]

    @pytest.mark.asyncio
    async def test_save_entity_validates_type(self):
        """Test entity type validation."""
        from src.tools.save_entity import save_entity_tool

        ctx = self._make_ctx()
        result_str = await save_entity_tool.on_invoke_tool(
            ctx,
            json.dumps({
                "name": "FastAPI",
                "entity_type": "invalid_type",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "error"
        assert "Invalid entity type" in result["message"]

    @pytest.mark.asyncio
    async def test_save_entity_rate_limited(self):
        """Test rate limiting."""
        with patch(
            "src.services.redis_service.check_graph_entity_rate_limit",
            new_callable=AsyncMock,
            return_value=(False, "Max 20 entities per conversation"),
        ):
            from src.tools.save_entity import save_entity_tool

            ctx = self._make_ctx()
            result_str = await save_entity_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "name": "FastAPI",
                    "entity_type": "tool",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "rate_limited"

    @pytest.mark.asyncio
    async def test_save_entity_requires_user_id(self):
        """Test that anonymous users cannot save entities."""
        from src.tools.save_entity import save_entity_tool

        ctx = self._make_ctx(user_id="anonymous")
        result_str = await save_entity_tool.on_invoke_tool(
            ctx,
            json.dumps({
                "name": "FastAPI",
                "entity_type": "tool",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "anonymous" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_save_entity_low_confidence_skipped(self):
        """Test that low confidence entities are skipped."""
        # Mock the settings to return a threshold
        mock_settings = MagicMock()
        mock_settings.graph_entity_confidence_threshold = 0.7

        with patch(
            "src.services.redis_service.check_graph_entity_rate_limit",
            new_callable=AsyncMock,
            return_value=(True, None),
        ), patch(
            "src.config.get_settings",
            return_value=mock_settings,
        ):
            from src.tools.save_entity import save_entity_tool

            ctx = self._make_ctx()
            result_str = await save_entity_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "name": "FastAPI",
                    "entity_type": "tool",
                    "confidence": 0.5,  # Below threshold
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "skipped"

    @pytest.mark.asyncio
    async def test_save_entity_all_types_valid(self):
        """Test all entity types are accepted."""
        valid_types = ["person", "project", "tool", "concept", "organization"]

        for entity_type in valid_types:
            mock_entity = self._make_mock_entity(entity_type=EntityType(entity_type))

            mock_service = MagicMock()
            mock_service.get_or_create_entity = AsyncMock(
                return_value=(mock_entity, True)
            )

            with patch(
                "src.services.redis_service.check_graph_entity_rate_limit",
                new_callable=AsyncMock,
                return_value=(True, None),
            ), patch(
                "src.services.graph_service.GraphService",
                return_value=mock_service,
            ):
                from src.tools.save_entity import save_entity_tool

                ctx = self._make_ctx()
                result_str = await save_entity_tool.on_invoke_tool(
                    ctx,
                    json.dumps({
                        "name": "Test",
                        "entity_type": entity_type,
                    }),
                )

            result = json.loads(result_str)
            assert result["success"] is True, f"Failed for type: {entity_type}"
