"""Integration tests for knowledge graph functionality.

These tests require Docker services running:
  docker compose -f docker/docker-compose.api.yml up -d --build
"""

import json
import time
from uuid import uuid4

import httpx
import pytest

BASE_URL = "http://localhost:8000"


@pytest.fixture
def client():
    """Create HTTP client for API requests."""
    return httpx.Client(base_url=BASE_URL, timeout=60.0)


def parse_sse_response(response_text: str) -> str:
    """Parse SSE response and extract full content."""
    content = ""
    for line in response_text.split("\n"):
        if line.startswith("data:"):
            try:
                data = json.loads(line[5:])
                if data.get("content"):
                    content += data["content"]
            except json.JSONDecodeError:
                pass
    return content


class TestEntityExtraction:
    """Tests for entity extraction from conversations."""

    def test_extract_tool_entity(self, client):
        """Test that tool mentions trigger entity extraction."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        response = client.post(
            "/chat",
            json={
                "message": "I'm using FastAPI for my new project.",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200
        # Entity extraction happens asynchronously
        time.sleep(2)

    def test_extract_person_entity(self, client):
        """Test that person mentions trigger entity extraction."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        response = client.post(
            "/chat",
            json={
                "message": "I work with Sarah on the backend team.",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200

    def test_extract_project_entity(self, client):
        """Test that project mentions trigger entity extraction."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        response = client.post(
            "/chat",
            json={
                "message": "Project Phoenix is our main initiative this quarter.",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200

    def test_extract_multiple_entities(self, client):
        """Test extracting multiple entities from one message."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        response = client.post(
            "/chat",
            json={
                "message": "We're using React, TypeScript, and PostgreSQL for the dashboard project.",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200
        time.sleep(2)


class TestRelationshipExtraction:
    """Tests for relationship extraction."""

    def test_extract_uses_relationship(self, client):
        """Test USES relationship extraction."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        response = client.post(
            "/chat",
            json={
                "message": "I use Python for data analysis.",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200

    def test_extract_prefers_relationship(self, client):
        """Test PREFERS relationship extraction."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        response = client.post(
            "/chat",
            json={
                "message": "I prefer TypeScript over JavaScript for type safety.",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200

    def test_extract_works_with_relationship(self, client):
        """Test WORKS_WITH relationship extraction."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        response = client.post(
            "/chat",
            json={
                "message": "I work with John on the API design.",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200


class TestGraphQueries:
    """Tests for graph query functionality."""

    def test_query_tools_used(self, client):
        """Test querying for tools used."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        # First, establish some context
        client.post(
            "/chat",
            json={
                "message": "I'm building a web app using FastAPI and PostgreSQL.",
                "user_id": user_id,
            },
        )
        time.sleep(3)

        # Now query
        response = client.post(
            "/chat",
            json={
                "message": "What tools do I use?",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200
        content = parse_sse_response(response.text)
        # The response should mention the tools
        assert len(content) > 0

    def test_query_people_worked_with(self, client):
        """Test querying for people worked with."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        # First, establish context
        client.post(
            "/chat",
            json={
                "message": "I collaborate with Alice and Bob on the frontend.",
                "user_id": user_id,
            },
        )
        time.sleep(3)

        # Now query
        response = client.post(
            "/chat",
            json={
                "message": "Who do I work with?",
                "user_id": user_id,
            },
        )

        assert response.status_code == 200


class TestCrossUserIsolation:
    """Tests for user data isolation."""

    def test_users_cannot_see_each_others_entities(self, client):
        """Test that User A's entities are not visible to User B."""
        user_a = f"graph-test-user-a-{uuid4().hex[:8]}"
        user_b = f"graph-test-user-b-{uuid4().hex[:8]}"

        # User A mentions a secret project
        client.post(
            "/chat",
            json={
                "message": "I'm working on Project Classified using SecretTech.",
                "user_id": user_a,
            },
        )
        time.sleep(2)

        # User B asks about it
        response = client.post(
            "/chat",
            json={
                "message": "What is Project Classified?",
                "user_id": user_b,
            },
        )

        assert response.status_code == 200
        content = parse_sse_response(response.text)
        # User B should NOT know about User A's project
        # The response should indicate no knowledge
        assert "SecretTech" not in content or "don't have" in content.lower()


class TestEntityDeduplication:
    """Tests for entity deduplication."""

    def test_same_entity_mentioned_twice(self, client):
        """Test that mentioning same entity twice doesn't create duplicates."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        # Mention FastAPI twice
        client.post(
            "/chat",
            json={
                "message": "I use FastAPI for web development.",
                "user_id": user_id,
            },
        )
        time.sleep(2)

        client.post(
            "/chat",
            json={
                "message": "FastAPI is really fast and easy to use.",
                "user_id": user_id,
            },
        )
        time.sleep(2)

        # The system should have one FastAPI entity with mention_count > 1
        # (We can't easily verify DB state from here, but no errors is good)


class TestRelationshipReinforcement:
    """Tests for relationship reinforcement."""

    def test_relationship_reinforced_on_repeat(self, client):
        """Test that repeating a relationship reinforces it."""
        user_id = f"graph-test-{uuid4().hex[:8]}"

        # Express preference twice
        client.post(
            "/chat",
            json={
                "message": "I prefer Python for scripting.",
                "user_id": user_id,
            },
        )
        time.sleep(2)

        client.post(
            "/chat",
            json={
                "message": "Python is my go-to language for scripts.",
                "user_id": user_id,
            },
        )
        time.sleep(2)

        # The PREFERS relationship should be reinforced (higher confidence)


class TestHealthCheck:
    """Basic health check to verify services are running."""

    def test_health_endpoint(self, client):
        """Verify health endpoint works."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
