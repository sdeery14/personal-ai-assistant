"""Unit tests for the query_graph tool."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.models.graph import EntityType, RelationshipType


class TestQueryGraphTool:
    """Tests for query_graph agent tool."""

    def _make_ctx(self, user_id="test-user"):
        """Create mock run context."""
        ctx = MagicMock()
        ctx.context = {
            "user_id": user_id,
            "correlation_id": uuid4(),
        }
        return ctx

    def _make_mock_entities(self):
        """Create mock entities."""
        from src.models.graph import Entity

        now = datetime.now(timezone.utc)
        return [
            Entity(
                id=uuid4(),
                user_id="test-user",
                name="FastAPI",
                canonical_name="fastapi",
                type=EntityType.TOOL,
                description="A web framework",
                confidence=0.9,
                mention_count=5,
                created_at=now,
                updated_at=now,
            ),
            Entity(
                id=uuid4(),
                user_id="test-user",
                name="PostgreSQL",
                canonical_name="postgresql",
                type=EntityType.TOOL,
                description="A database",
                confidence=0.9,
                mention_count=3,
                created_at=now,
                updated_at=now,
            ),
        ]

    def _make_mock_relationships(self, source_id=None, target_id=None):
        """Create mock relationships."""
        from src.models.graph import Relationship

        now = datetime.now(timezone.utc)
        return [
            Relationship(
                id=uuid4(),
                user_id="test-user",
                source_entity_id=source_id or uuid4(),
                target_entity_id=target_id or uuid4(),
                relationship_type=RelationshipType.USES,
                confidence=0.9,
                created_at=now,
            )
        ]

    @pytest.mark.asyncio
    async def test_query_graph_returns_entities(self):
        """Test querying returns matching entities."""
        mock_entities = self._make_mock_entities()
        mock_relationships = self._make_mock_relationships()

        mock_service = MagicMock()
        mock_service.search_entities = AsyncMock(return_value=mock_entities)
        mock_service.get_entity_relationships = AsyncMock(
            return_value=mock_relationships
        )
        mock_service.get_related_entities = AsyncMock(return_value=[])

        with patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.query_graph import query_graph_tool

            ctx = self._make_ctx()
            result_str = await query_graph_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "query": "tools",
                    "entity_type": "tool",
                }),
            )

        result = json.loads(result_str)
        assert len(result["entities"]) == 2
        assert result["metadata"]["count"] == 2

    @pytest.mark.asyncio
    async def test_query_graph_empty_results(self):
        """Test querying with no matches."""
        mock_service = MagicMock()
        mock_service.search_entities = AsyncMock(return_value=[])

        with patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.query_graph import query_graph_tool

            ctx = self._make_ctx()
            result_str = await query_graph_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "query": "nonexistent",
                }),
            )

        result = json.loads(result_str)
        assert len(result["entities"]) == 0
        assert result["metadata"]["count"] == 0

    @pytest.mark.asyncio
    async def test_query_graph_validates_entity_type(self):
        """Test entity type validation."""
        from src.tools.query_graph import query_graph_tool

        ctx = self._make_ctx()
        result_str = await query_graph_tool.on_invoke_tool(
            ctx,
            json.dumps({
                "query": "test",
                "entity_type": "invalid_type",
            }),
        )

        result = json.loads(result_str)
        assert result["metadata"].get("error") is not None
        assert "Invalid entity type" in result["metadata"]["error"]

    @pytest.mark.asyncio
    async def test_query_graph_validates_relationship_type(self):
        """Test relationship type validation."""
        from src.tools.query_graph import query_graph_tool

        ctx = self._make_ctx()
        result_str = await query_graph_tool.on_invoke_tool(
            ctx,
            json.dumps({
                "query": "test",
                "relationship_type": "INVALID_REL",
            }),
        )

        result = json.loads(result_str)
        assert result["metadata"].get("error") is not None
        assert "Invalid relationship type" in result["metadata"]["error"]

    @pytest.mark.asyncio
    async def test_query_graph_requires_user_id(self):
        """Test that anonymous users cannot query."""
        from src.tools.query_graph import query_graph_tool

        ctx = self._make_ctx(user_id="anonymous")
        result_str = await query_graph_tool.on_invoke_tool(
            ctx,
            json.dumps({
                "query": "test",
            }),
        )

        result = json.loads(result_str)
        assert "error" in result["metadata"]
        assert "anonymous" in result["metadata"]["error"].lower()

    @pytest.mark.asyncio
    async def test_query_graph_includes_relationships(self):
        """Test that response includes relationship info."""
        mock_entities = self._make_mock_entities()[:1]
        mock_relationships = self._make_mock_relationships(
            source_id=mock_entities[0].id
        )

        mock_service = MagicMock()
        mock_service.search_entities = AsyncMock(return_value=mock_entities)
        mock_service.get_entity_relationships = AsyncMock(
            return_value=mock_relationships
        )
        mock_service.get_related_entities = AsyncMock(
            return_value=self._make_mock_entities()[1:]
        )

        with patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.query_graph import query_graph_tool

            ctx = self._make_ctx()
            result_str = await query_graph_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "query": "FastAPI",
                }),
            )

        result = json.loads(result_str)
        assert len(result["entities"]) == 1
        entity = result["entities"][0]
        assert entity["name"] == "FastAPI"
        assert "relationships" in entity
        assert "related_to" in entity

    @pytest.mark.asyncio
    async def test_query_graph_filters_by_entity_type(self):
        """Test filtering by entity type."""
        mock_entities = self._make_mock_entities()

        mock_service = MagicMock()
        mock_service.search_entities = AsyncMock(return_value=mock_entities)
        mock_service.get_entity_relationships = AsyncMock(return_value=[])
        mock_service.get_related_entities = AsyncMock(return_value=[])

        with patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.query_graph import query_graph_tool

            ctx = self._make_ctx()
            await query_graph_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "query": "",
                    "entity_type": "tool",
                }),
            )

        # Verify search_entities was called with type filter
        call_args = mock_service.search_entities.call_args
        assert call_args.kwargs.get("entity_type") == EntityType.TOOL

    @pytest.mark.asyncio
    async def test_query_graph_includes_metadata(self):
        """Test response includes proper metadata."""
        mock_entities = self._make_mock_entities()
        mock_relationships = self._make_mock_relationships()

        mock_service = MagicMock()
        mock_service.search_entities = AsyncMock(return_value=mock_entities)
        mock_service.get_entity_relationships = AsyncMock(
            return_value=mock_relationships
        )
        mock_service.get_related_entities = AsyncMock(return_value=[])

        with patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.query_graph import query_graph_tool

            ctx = self._make_ctx()
            result_str = await query_graph_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "query": "tools",
                    "limit": 10,
                }),
            )

        result = json.loads(result_str)
        metadata = result["metadata"]
        assert "count" in metadata
        assert "query" in metadata
        assert "query_time_ms" in metadata
        assert metadata["query"] == "tools"

    @pytest.mark.asyncio
    async def test_query_graph_respects_limit(self):
        """Test that limit is passed to search."""
        mock_entities = self._make_mock_entities()[:1]

        mock_service = MagicMock()
        mock_service.search_entities = AsyncMock(return_value=mock_entities)
        mock_service.get_entity_relationships = AsyncMock(return_value=[])
        mock_service.get_related_entities = AsyncMock(return_value=[])

        with patch(
            "src.services.graph_service.GraphService",
            return_value=mock_service,
        ):
            from src.tools.query_graph import query_graph_tool

            ctx = self._make_ctx()
            await query_graph_tool.on_invoke_tool(
                ctx,
                json.dumps({
                    "query": "test",
                    "limit": 5,
                }),
            )

        call_args = mock_service.search_entities.call_args
        assert call_args.kwargs.get("limit") == 5
