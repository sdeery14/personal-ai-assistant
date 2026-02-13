"""Unit tests for entity browsing API endpoints (T070).

Tests /entities endpoints with mocked GraphService
and dependency overrides for authentication.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.models.graph import Entity, EntityType, Relationship, RelationshipType
from src.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    user_id=None,
    username="testuser",
    display_name="Test User",
    is_admin=False,
    is_active=True,
):
    """Create a User model for test assertions."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        username=username,
        display_name=display_name,
        is_admin=is_admin,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


def _make_entity(
    entity_id=None,
    user_id=None,
    name="Python",
    entity_type=EntityType.TOOL,
    description="A programming language",
    aliases=None,
    confidence=0.95,
    mention_count=3,
):
    """Create an Entity model for test data."""
    now = datetime.now(timezone.utc)
    return Entity(
        id=entity_id or uuid4(),
        user_id=user_id or str(uuid4()),
        name=name,
        canonical_name=name.lower(),
        type=entity_type,
        aliases=aliases or [],
        description=description,
        confidence=confidence,
        mention_count=mention_count,
        created_at=now,
        updated_at=now,
        last_mentioned_at=now,
    )


def _make_relationship(
    rel_id=None,
    user_id=None,
    source_entity_id=None,
    target_entity_id=None,
    rel_type=RelationshipType.USES,
    context="User uses this tool",
    confidence=0.9,
):
    """Create a Relationship model for test data."""
    now = datetime.now(timezone.utc)
    return Relationship(
        id=rel_id or uuid4(),
        user_id=user_id or str(uuid4()),
        source_entity_id=source_entity_id or uuid4(),
        target_entity_id=target_entity_id,
        relationship_type=rel_type,
        context=context,
        confidence=confidence,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def current_user():
    """A pre-built authenticated user."""
    return _make_user(username="alice", display_name="Alice")


@pytest.fixture
def client(current_user):
    """Create a TestClient with lifespan mocked and auth overridden."""
    with (
        patch("src.database.init_database", new_callable=AsyncMock),
        patch("src.database.run_migrations", new_callable=AsyncMock),
        patch("src.services.redis_service.get_redis", new_callable=AsyncMock),
        patch("src.database.close_database", new_callable=AsyncMock),
        patch("src.services.redis_service.close_redis", new_callable=AsyncMock),
        patch("src.services.memory_write_service.await_pending_writes", new_callable=AsyncMock),
    ):
        from fastapi.testclient import TestClient
        from src.api.dependencies import get_current_user
        from src.main import app

        app.dependency_overrides[get_current_user] = lambda: current_user

        with TestClient(app) as tc:
            yield tc

        app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# GET /entities
# ---------------------------------------------------------------------------

class TestListEntities:
    """Tests for GET /entities."""

    def test_returns_paginated_list(self, client, current_user):
        user_id = str(current_user.id)
        entities = [
            _make_entity(user_id=user_id, name="Python", entity_type=EntityType.TOOL),
            _make_entity(user_id=user_id, name="FastAPI", entity_type=EntityType.TOOL),
        ]

        with patch("src.api.entities.GraphService") as MockService:
            svc = MockService.return_value
            svc.search_entities = AsyncMock(return_value=entities)

            response = client.get("/entities")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2
        assert body["items"][0]["name"] == "Python"
        assert body["items"][1]["name"] == "FastAPI"
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_filters_by_search_query(self, client, current_user):
        user_id = str(current_user.id)
        entities = [
            _make_entity(user_id=user_id, name="Python", entity_type=EntityType.TOOL),
        ]

        with patch("src.api.entities.GraphService") as MockService:
            svc = MockService.return_value
            svc.search_entities = AsyncMock(return_value=entities)

            response = client.get("/entities?q=Python")

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["name"] == "Python"

        # Verify search_entities was called with name_pattern
        svc.search_entities.assert_called_once()
        call_kwargs = svc.search_entities.call_args
        assert call_kwargs.kwargs.get("name_pattern") == "Python" or \
            (len(call_kwargs.args) > 1 and call_kwargs.args[1] == "Python")

    def test_filters_by_type(self, client, current_user):
        user_id = str(current_user.id)
        entities = [
            _make_entity(user_id=user_id, name="Alice", entity_type=EntityType.PERSON),
        ]

        with patch("src.api.entities.GraphService") as MockService:
            svc = MockService.return_value
            svc.search_entities = AsyncMock(return_value=entities)

            response = client.get("/entities?type=person")

        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["type"] == "person"

    def test_returns_empty_list_when_no_entities(self, client, current_user):
        with patch("src.api.entities.GraphService") as MockService:
            svc = MockService.return_value
            svc.search_entities = AsyncMock(return_value=[])

            response = client.get("/entities")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_user_isolation_scoped_to_current_user(self, client, current_user):
        """Verify that search_entities is called with the current user's ID."""
        with patch("src.api.entities.GraphService") as MockService:
            svc = MockService.return_value
            svc.search_entities = AsyncMock(return_value=[])

            response = client.get("/entities")

        assert response.status_code == 200
        svc.search_entities.assert_called_once()
        call_kwargs = svc.search_entities.call_args
        assert call_kwargs.kwargs.get("user_id") == str(current_user.id) or \
            (len(call_kwargs.args) > 0 and call_kwargs.args[0] == str(current_user.id))


# ---------------------------------------------------------------------------
# GET /entities/{id}/relationships
# ---------------------------------------------------------------------------

class TestGetEntityRelationships:
    """Tests for GET /entities/{id}/relationships."""

    def test_returns_relationships_list(self, client, current_user):
        user_id = str(current_user.id)
        entity_id = uuid4()
        target_id = uuid4()

        entity = _make_entity(
            entity_id=entity_id,
            user_id=user_id,
            name="Python",
            entity_type=EntityType.TOOL,
        )
        target_entity = _make_entity(
            entity_id=target_id,
            user_id=user_id,
            name="FastAPI",
            entity_type=EntityType.TOOL,
        )
        relationship = _make_relationship(
            user_id=user_id,
            source_entity_id=entity_id,
            target_entity_id=target_id,
            rel_type=RelationshipType.DEPENDS_ON,
            context="FastAPI depends on Python",
        )

        with patch("src.api.entities.GraphService") as MockService:
            svc = MockService.return_value
            svc.get_entity_by_id = AsyncMock(
                side_effect=lambda eid, uid: {
                    entity_id: entity,
                    target_id: target_entity,
                }.get(eid)
            )
            svc.get_entity_relationships = AsyncMock(return_value=[relationship])

            response = client.get(f"/entities/{entity_id}/relationships")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["relationship_type"] == "DEPENDS_ON"
        assert body[0]["source_entity"]["name"] == "Python"
        assert body[0]["target_entity"]["name"] == "FastAPI"
        assert body[0]["context"] == "FastAPI depends on Python"

    def test_returns_404_when_entity_not_found(self, client, current_user):
        nonexistent_id = uuid4()

        with patch("src.api.entities.GraphService") as MockService:
            svc = MockService.return_value
            svc.get_entity_by_id = AsyncMock(return_value=None)

            response = client.get(f"/entities/{nonexistent_id}/relationships")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
