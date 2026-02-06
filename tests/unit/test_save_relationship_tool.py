"""Unit tests for the save_relationship tool."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.models.graph import EntityType, RelationshipType


class TestSaveRelationshipTool:
    """Tests for save_relationship agent tool."""

    def _make_ctx(self, user_id="test-user", conversation_id=None):
        """Create mock run context."""
        ctx = MagicMock()
        ctx.context = {
            "user_id": user_id,
            "correlation_id": uuid4(),
            "conversation_id": conversation_id or str(uuid4()),
        }
        return ctx

    def _make_mock_entity(self, name="FastAPI", entity_type=EntityType.TOOL):
        """Create a mock entity."""
        from src.models.graph import Entity

        return Entity(
            id=uuid4(),
            user_id="test-user",
            name=name,
            canonical_name=name.lower(),
            type=entity_type,
            confidence=0.9,
            mention_count=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def _make_mock_relationship(self, source_id=None, target_id=None):
        """Create a mock relationship."""
        from src.models.graph import Relationship

        return Relationship(
            id=uuid4(),
            user_id="test-user",
            source_entity_id=source_id or uuid4(),
            target_entity_id=target_id or uuid4(),
            relationship_type=RelationshipType.USES,
            confidence=0.9,
            created_at=datetime.now(timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_save_relationship_creates_new(self):
        """Test creating a new relationship."""
        source_entity = self._make_mock_entity("Project Phoenix", EntityType.PROJECT)
        target_entity = self._make_mock_entity("FastAPI", EntityType.TOOL)
        mock_relationship = self._make_mock_relationship(source_entity.id, target_entity.id)

        mock_service = MagicMock()
        mock_service.get_or_create_entity = AsyncMock(
            side_effect=[(source_entity, True), (target_entity, True)]
        )
        mock_service.get_or_create_relationship = AsyncMock(
            return_value=(mock_relationship, True)
        )

        with patch(
            "src.services.redis_service.check_graph_relationship_rate_limit",
            new_callable=AsyncMock,
            return_value=(True, None),
        ), patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.save_relationship import save_relationship_tool

            ctx = self._make_ctx()
            result_str = await save_relationship_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "source_entity_name": "Project Phoenix",
                    "source_entity_type": "project",
                    "relationship_type": "USES",
                    "target_entity_name": "FastAPI",
                    "target_entity_type": "tool",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["action"] == "created"
        assert result["relationship_type"] == "USES"

    @pytest.mark.asyncio
    async def test_save_relationship_reinforces_existing(self):
        """Test reinforcing an existing relationship."""
        source_entity = self._make_mock_entity("Project Phoenix", EntityType.PROJECT)
        target_entity = self._make_mock_entity("FastAPI", EntityType.TOOL)
        mock_relationship = self._make_mock_relationship(source_entity.id, target_entity.id)

        mock_service = MagicMock()
        mock_service.get_or_create_entity = AsyncMock(
            side_effect=[(source_entity, False), (target_entity, False)]
        )
        mock_service.get_or_create_relationship = AsyncMock(
            return_value=(mock_relationship, False)  # Not created, reinforced
        )

        with patch(
            "src.services.redis_service.check_graph_relationship_rate_limit",
            new_callable=AsyncMock,
            return_value=(True, None),
        ), patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.save_relationship import save_relationship_tool

            ctx = self._make_ctx()
            result_str = await save_relationship_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "source_entity_name": "Project Phoenix",
                    "source_entity_type": "project",
                    "relationship_type": "USES",
                    "target_entity_name": "FastAPI",
                    "target_entity_type": "tool",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
        assert result["action"] == "reinforced"

    @pytest.mark.asyncio
    async def test_save_relationship_validates_source_type(self):
        """Test source entity type validation."""
        from src.tools.save_relationship import save_relationship_tool

        ctx = self._make_ctx()
        result_str = await save_relationship_tool.on_invoke_tool(
            ctx,
            json.dumps({
                "source_entity_name": "test",
                "source_entity_type": "invalid_type",
                "relationship_type": "USES",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid source entity type" in result["message"]

    @pytest.mark.asyncio
    async def test_save_relationship_validates_target_type(self):
        """Test target entity type validation."""
        from src.tools.save_relationship import save_relationship_tool

        ctx = self._make_ctx()
        result_str = await save_relationship_tool.on_invoke_tool(
            ctx,
            json.dumps({
                "source_entity_name": "test",
                "source_entity_type": "project",
                "relationship_type": "USES",
                "target_entity_name": "target",
                "target_entity_type": "invalid_type",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid target entity type" in result["message"]

    @pytest.mark.asyncio
    async def test_save_relationship_validates_relationship_type(self):
        """Test relationship type validation."""
        from src.tools.save_relationship import save_relationship_tool

        ctx = self._make_ctx()
        result_str = await save_relationship_tool.on_invoke_tool(
            ctx,
            json.dumps({
                "source_entity_name": "test",
                "source_entity_type": "project",
                "relationship_type": "INVALID_REL",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "Invalid relationship type" in result["message"]

    @pytest.mark.asyncio
    async def test_save_relationship_rate_limited(self):
        """Test rate limiting."""
        with patch(
            "src.services.redis_service.check_graph_relationship_rate_limit",
            new_callable=AsyncMock,
            return_value=(False, "Max 30 relationships per conversation"),
        ):
            from src.tools.save_relationship import save_relationship_tool

            ctx = self._make_ctx()
            result_str = await save_relationship_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "source_entity_name": "test",
                    "source_entity_type": "project",
                    "relationship_type": "USES",
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is False
        assert result["action"] == "rate_limited"

    @pytest.mark.asyncio
    async def test_save_relationship_requires_user_id(self):
        """Test that anonymous users cannot save relationships."""
        from src.tools.save_relationship import save_relationship_tool

        ctx = self._make_ctx(user_id="anonymous")
        result_str = await save_relationship_tool.on_invoke_tool(
            ctx,
            json.dumps({
                "source_entity_name": "test",
                "source_entity_type": "project",
                "relationship_type": "USES",
            }),
        )

        result = json.loads(result_str)
        assert result["success"] is False
        assert "anonymous" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_save_relationship_all_types_valid(self):
        """Test all relationship types are accepted."""
        valid_types = [
            "USES",
            "PREFERS",
            "DECIDED",
            "WORKS_ON",
            "WORKS_WITH",
            "KNOWS",
            "DEPENDS_ON",
            "PART_OF",
        ]

        for rel_type in valid_types:
            source_entity = self._make_mock_entity("user", EntityType.PERSON)
            target_entity = self._make_mock_entity("target", EntityType.TOOL)
            mock_relationship = self._make_mock_relationship()
            mock_relationship.relationship_type = RelationshipType(rel_type)

            mock_service = MagicMock()
            mock_service.get_or_create_entity = AsyncMock(
                side_effect=[(source_entity, True), (target_entity, True)]
            )
            mock_service.get_or_create_relationship = AsyncMock(
                return_value=(mock_relationship, True)
            )

            with patch(
                "src.services.redis_service.check_graph_relationship_rate_limit",
                new_callable=AsyncMock,
                return_value=(True, None),
            ), patch(
                "src.services.graph_service.GraphService",
                return_value=mock_service,
            ):
                from src.tools.save_relationship import save_relationship_tool

                ctx = self._make_ctx()
                result_str = await save_relationship_tool.on_invoke_tool(
                    ctx,
                    json.dumps({
                        "source_entity_name": "test",
                        "source_entity_type": "person",
                        "relationship_type": rel_type,
                        "target_entity_name": "target",
                        "target_entity_type": "tool",
                    }),
                )

            result = json.loads(result_str)
            assert result["success"] is True, f"Failed for type: {rel_type}"

    @pytest.mark.asyncio
    async def test_save_relationship_without_target(self):
        """Test creating relationship without target entity."""
        source_entity = self._make_mock_entity("user", EntityType.PERSON)
        mock_relationship = self._make_mock_relationship()
        mock_relationship.target_entity_id = None

        mock_service = MagicMock()
        mock_service.get_or_create_entity = AsyncMock(
            return_value=(source_entity, True)
        )
        mock_service.get_or_create_relationship = AsyncMock(
            return_value=(mock_relationship, True)
        )

        with patch(
            "src.services.redis_service.check_graph_relationship_rate_limit",
            new_callable=AsyncMock,
            return_value=(True, None),
        ), patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.save_relationship import save_relationship_tool

            ctx = self._make_ctx()
            result_str = await save_relationship_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "source_entity_name": "user",
                    "source_entity_type": "person",
                    "relationship_type": "DECIDED",
                    # No target entity
                }),
            )

        result = json.loads(result_str)
        assert result["success"] is True
