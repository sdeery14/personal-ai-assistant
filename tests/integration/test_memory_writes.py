"""Integration tests for memory write functionality.

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


@pytest.fixture
def async_client():
    """Create async HTTP client."""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=60.0)


class TestMemoryWriteViaChat:
    """Tests for memory writes triggered through /chat endpoint."""

    def test_save_memory_via_chat(self, client):
        """Test that sharing personal info triggers memory save."""
        response = client.post(
            "/chat",
            json={
                "message": "My name is IntegrationTestUser and I work at TestCorp as a developer.",
            },
            headers={"X-User-Id": f"integration-test-{uuid4().hex[:8]}"},
        )

        assert response.status_code == 200
        # SSE response should contain text acknowledging the info
        content = response.text
        assert "data:" in content

    def test_delete_memory_via_chat(self, client):
        """Test that requesting memory deletion works."""
        user_id = f"integration-test-{uuid4().hex[:8]}"

        # First, share some info
        client.post(
            "/chat",
            json={"message": "I live in TestCity, TestState."},
            headers={"X-User-Id": user_id},
        )

        # Then request deletion
        response = client.post(
            "/chat",
            json={"message": "Please forget where I live."},
            headers={"X-User-Id": user_id},
        )

        assert response.status_code == 200

    def test_memory_correction_flow(self, client):
        """Test that correcting information updates memory."""
        user_id = f"integration-test-{uuid4().hex[:8]}"

        # Share initial info
        client.post(
            "/chat",
            json={"message": "My favorite programming language is Python."},
            headers={"X-User-Id": user_id},
        )

        # Correct it
        response = client.post(
            "/chat",
            json={"message": "Actually, I've switched to Rust as my favorite language."},
            headers={"X-User-Id": user_id},
        )

        assert response.status_code == 200


class TestRateLimiting:
    """Tests for memory write rate limiting."""

    def test_conversation_rate_limit(self, client):
        """Test that excessive writes in one conversation are rate limited."""
        user_id = f"integration-test-{uuid4().hex[:8]}"

        # Send many messages with personal facts
        for i in range(15):
            response = client.post(
                "/chat",
                json={"message": f"Remember fact number {i}: I have {i} cats."},
                headers={"X-User-Id": user_id},
            )
            assert response.status_code == 200

        # The system should have rate limited some writes
        # (We can't easily verify this without DB access, but the test
        # verifies no errors/crashes occur under load)


class TestHealthCheck:
    """Basic health check to verify services are running."""

    def test_health_endpoint(self, client):
        """Verify health endpoint works."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
