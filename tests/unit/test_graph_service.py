"""Unit tests for the graph service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from src.models.graph import EntityType, RelationshipType
from src.services.graph_service import (
    GraphService,
    normalize_entity_name,
    embedding_to_pgvector,
    pgvector_to_embedding,
)


class TestNormalizeEntityName:
    """Tests for entity name normalization."""

    def test_lowercase_conversion(self):
        assert normalize_entity_name("FastAPI") == "fastapi"
        assert normalize_entity_name("PostgreSQL") == "postgresql"

    def test_strip_whitespace(self):
        assert normalize_entity_name("  FastAPI  ") == "fastapi"
        assert normalize_entity_name("\tDocker\n") == "docker"

    def test_collapse_multiple_spaces(self):
        assert normalize_entity_name("project  phoenix") == "project phoenix"
        assert normalize_entity_name("my   cool   project") == "my cool project"

    def test_remove_articles(self):
        assert normalize_entity_name("the project") == "project"
        assert normalize_entity_name("a framework") == "framework"
        assert normalize_entity_name("an API") == "api"

    def test_empty_string(self):
        assert normalize_entity_name("") == ""
        assert normalize_entity_name("   ") == ""

    def test_preserves_meaningful_content(self):
        assert normalize_entity_name("React Native") == "react native"
        assert normalize_entity_name("Sarah Johnson") == "sarah johnson"


class TestEmbeddingConversion:
    """Tests for pgvector embedding conversion."""

    def test_embedding_to_pgvector(self):
        embedding = [0.1, 0.2, 0.3]
        result = embedding_to_pgvector(embedding)
        assert result == "[0.1,0.2,0.3]"

    def test_embedding_to_pgvector_none(self):
        assert embedding_to_pgvector(None) is None

    def test_pgvector_to_embedding(self):
        pgvector_str = "[0.1,0.2,0.3]"
        result = pgvector_to_embedding(pgvector_str)
        assert result == [0.1, 0.2, 0.3]

    def test_pgvector_to_embedding_none(self):
        assert pgvector_to_embedding(None) is None

    def test_pgvector_to_embedding_already_list(self):
        embedding = [0.1, 0.2, 0.3]
        result = pgvector_to_embedding(embedding)
        assert result == embedding

    def test_pgvector_to_embedding_empty(self):
        assert pgvector_to_embedding("[]") == []


class TestGraphServiceEntity:
    """Tests for entity operations."""

    @pytest.fixture
    def mock_pool(self):
        """Create mock database pool with proper async context manager."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        # Create a context manager mock
        class MockPoolAcquire:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_pool = MagicMock()
        mock_pool.acquire.return_value = MockPoolAcquire()

        return mock_pool, mock_conn

    @pytest.fixture
    def graph_service(self):
        """Create graph service with mocked dependencies."""
        service = GraphService()
        service.embedding_service = MagicMock()
        service.embedding_service.get_embedding = AsyncMock(
            return_value=[0.1] * 1536
        )
        return service

    @pytest.mark.asyncio
    async def test_get_entity_by_id_found(self, graph_service, mock_pool):
        """Test retrieving an entity by ID."""
        pool, conn = mock_pool
        entity_id = uuid4()
        user_id = "test-user"
        now = datetime.now(timezone.utc)

        conn.fetchrow.return_value = {
            "id": entity_id,
            "user_id": user_id,
            "name": "FastAPI",
            "canonical_name": "fastapi",
            "type": "tool",
            "aliases": [],
            "description": "A web framework",
            "embedding": "[0.1,0.2]",
            "confidence": 0.9,
            "mention_count": 5,
            "first_seen_message_id": None,
            "first_seen_conversation_id": None,
            "last_mentioned_at": now,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }

        with patch("src.services.graph_service.get_pool", return_value=pool):
            entity = await graph_service.get_entity_by_id(entity_id, user_id)

        assert entity is not None
        assert entity.id == entity_id
        assert entity.name == "FastAPI"
        assert entity.type == EntityType.TOOL

    @pytest.mark.asyncio
    async def test_get_entity_by_id_not_found(self, graph_service, mock_pool):
        """Test retrieving non-existent entity."""
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.graph_service.get_pool", return_value=pool):
            entity = await graph_service.get_entity_by_id(uuid4(), "test-user")

        assert entity is None

    @pytest.mark.asyncio
    async def test_create_entity(self, graph_service, mock_pool):
        """Test creating a new entity."""
        pool, conn = mock_pool
        entity_id = uuid4()
        now = datetime.now(timezone.utc)

        conn.fetchrow.return_value = {
            "id": entity_id,
            "mention_count": 1,
            "created_at": now,
        }

        with patch("src.services.graph_service.get_pool", return_value=pool):
            entity = await graph_service.create_entity(
                user_id="test-user",
                name="FastAPI",
                entity_type=EntityType.TOOL,
                description="A web framework",
                confidence=0.9,
            )

        assert entity.name == "FastAPI"
        assert entity.type == EntityType.TOOL
        assert entity.canonical_name == "fastapi"
        conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_entity_creates_new(self, graph_service, mock_pool):
        """Test get_or_create creates new entity when not found."""
        pool, conn = mock_pool
        entity_id = uuid4()
        now = datetime.now(timezone.utc)

        # First call returns None (not found), second call creates
        conn.fetchrow.side_effect = [
            None,  # get_entity_by_canonical_name
            {"id": entity_id, "mention_count": 1, "created_at": now},  # create
        ]

        with patch("src.services.graph_service.get_pool", return_value=pool):
            entity, created = await graph_service.get_or_create_entity(
                user_id="test-user",
                name="FastAPI",
                entity_type=EntityType.TOOL,
            )

        assert created is True
        assert entity.name == "FastAPI"

    @pytest.mark.asyncio
    async def test_get_or_create_entity_returns_existing(self, graph_service, mock_pool):
        """Test get_or_create returns existing entity."""
        pool, conn = mock_pool
        entity_id = uuid4()
        now = datetime.now(timezone.utc)

        existing_entity = {
            "id": entity_id,
            "user_id": "test-user",
            "name": "FastAPI",
            "canonical_name": "fastapi",
            "type": "tool",
            "aliases": [],
            "description": None,
            "embedding": None,
            "confidence": 0.9,
            "mention_count": 3,
            "first_seen_message_id": None,
            "first_seen_conversation_id": None,
            "last_mentioned_at": now,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }

        # Return existing entity, then updated entity after mention update
        conn.fetchrow.side_effect = [existing_entity, existing_entity]
        conn.execute.return_value = "UPDATE 1"

        with patch("src.services.graph_service.get_pool", return_value=pool):
            entity, created = await graph_service.get_or_create_entity(
                user_id="test-user",
                name="FastAPI",
                entity_type=EntityType.TOOL,
            )

        assert created is False
        assert entity.id == entity_id

    @pytest.mark.asyncio
    async def test_search_entities(self, graph_service, mock_pool):
        """Test searching entities."""
        pool, conn = mock_pool
        now = datetime.now(timezone.utc)

        conn.fetch.return_value = [
            {
                "id": uuid4(),
                "user_id": "test-user",
                "name": "FastAPI",
                "canonical_name": "fastapi",
                "type": "tool",
                "aliases": [],
                "description": None,
                "embedding": None,
                "confidence": 0.9,
                "mention_count": 5,
                "first_seen_message_id": None,
                "first_seen_conversation_id": None,
                "last_mentioned_at": now,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
        ]

        with patch("src.services.graph_service.get_pool", return_value=pool):
            entities = await graph_service.search_entities(
                user_id="test-user",
                name_pattern="fast",
                entity_type=EntityType.TOOL,
            )

        assert len(entities) == 1
        assert entities[0].name == "FastAPI"

    @pytest.mark.asyncio
    async def test_user_id_scoping_in_queries(self, graph_service, mock_pool):
        """Test that all queries include user_id scoping."""
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.graph_service.get_pool", return_value=pool):
            await graph_service.get_entity_by_id(uuid4(), "user-123")

        # Verify user_id was passed in the query
        call_args = conn.fetchrow.call_args
        assert "user-123" in call_args[0]


class TestGraphServiceRelationship:
    """Tests for relationship operations."""

    @pytest.fixture
    def mock_pool(self):
        """Create mock database pool with proper async context manager."""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        class MockPoolAcquire:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_pool = MagicMock()
        mock_pool.acquire.return_value = MockPoolAcquire()

        return mock_pool, mock_conn

    @pytest.fixture
    def graph_service(self):
        """Create graph service with mocked dependencies."""
        service = GraphService()
        service.embedding_service = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_create_relationship(self, graph_service, mock_pool):
        """Test creating a relationship."""
        pool, conn = mock_pool
        source_id = uuid4()
        target_id = uuid4()

        conn.execute.return_value = "INSERT 1"

        with patch("src.services.graph_service.get_pool", return_value=pool):
            relationship = await graph_service.create_relationship(
                user_id="test-user",
                source_entity_id=source_id,
                target_entity_id=target_id,
                relationship_type=RelationshipType.USES,
                context="for web development",
            )

        assert relationship.source_entity_id == source_id
        assert relationship.target_entity_id == target_id
        assert relationship.relationship_type == RelationshipType.USES

    @pytest.mark.asyncio
    async def test_get_or_create_relationship_creates_new(self, graph_service, mock_pool):
        """Test creating new relationship when none exists."""
        pool, conn = mock_pool
        source_id = uuid4()
        target_id = uuid4()

        conn.fetchrow.return_value = None  # No existing relationship
        conn.execute.return_value = "INSERT 1"

        with patch("src.services.graph_service.get_pool", return_value=pool):
            relationship, created = await graph_service.get_or_create_relationship(
                user_id="test-user",
                source_entity_id=source_id,
                target_entity_id=target_id,
                relationship_type=RelationshipType.USES,
            )

        assert created is True

    @pytest.mark.asyncio
    async def test_get_or_create_relationship_reinforces_existing(
        self, graph_service, mock_pool
    ):
        """Test reinforcing existing relationship."""
        pool, conn = mock_pool
        rel_id = uuid4()
        source_id = uuid4()
        target_id = uuid4()
        now = datetime.now(timezone.utc)

        existing = {
            "id": rel_id,
            "user_id": "test-user",
            "source_entity_id": source_id,
            "target_entity_id": target_id,
            "relationship_type": "USES",
            "context": None,
            "confidence": 0.8,
            "source_message_id": None,
            "source_conversation_id": None,
            "created_at": now,
            "deleted_at": None,
        }

        conn.fetchrow.return_value = existing
        conn.execute.return_value = "UPDATE 1"

        with patch("src.services.graph_service.get_pool", return_value=pool):
            relationship, created = await graph_service.get_or_create_relationship(
                user_id="test-user",
                source_entity_id=source_id,
                target_entity_id=target_id,
                relationship_type=RelationshipType.USES,
            )

        assert created is False
        assert relationship.id == rel_id

    @pytest.mark.asyncio
    async def test_get_entity_relationships(self, graph_service, mock_pool):
        """Test getting relationships for an entity."""
        pool, conn = mock_pool
        entity_id = uuid4()
        now = datetime.now(timezone.utc)

        conn.fetch.return_value = [
            {
                "id": uuid4(),
                "user_id": "test-user",
                "source_entity_id": entity_id,
                "target_entity_id": uuid4(),
                "relationship_type": "USES",
                "context": None,
                "confidence": 0.9,
                "source_message_id": None,
                "source_conversation_id": None,
                "created_at": now,
                "deleted_at": None,
            }
        ]

        with patch("src.services.graph_service.get_pool", return_value=pool):
            relationships = await graph_service.get_entity_relationships(
                entity_id=entity_id,
                user_id="test-user",
            )

        assert len(relationships) >= 1
