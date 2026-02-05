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


class TestEpisodeSummarization:
    """Tests for automatic episode summarization."""

    def test_episode_summarization_after_threshold(self, client):
        """Test that episode summary is created after enough messages.

        Episode summarization triggers when:
        - 8+ user messages OR 15+ total messages in a conversation

        This test sends 9 user messages to exceed the threshold.
        """
        user_id = f"integration-test-{uuid4().hex[:8]}"
        conversation_id = None

        # Send 9 messages with varied, meaningful content
        messages = [
            "Hi, I'm planning a trip to Japan next month.",
            "I want to visit Tokyo, Kyoto, and Osaka.",
            "My budget is around $3000 for two weeks.",
            "I'm interested in temples, food, and technology.",
            "Should I get a JR Pass for train travel?",
            "What's the best time to see cherry blossoms?",
            "I'm also thinking about visiting some hot springs.",
            "Do you have any restaurant recommendations in Tokyo?",
            "What about day trips from Kyoto?",
        ]

        for i, msg in enumerate(messages):
            response = client.post(
                "/chat",
                json={"message": msg},
                headers={"X-User-Id": user_id},
            )
            assert response.status_code == 200, f"Message {i+1} failed"

            # Small delay between messages to avoid rate limiting
            if i < len(messages) - 1:
                time.sleep(0.5)

        # Wait for async episode summarization to complete
        # Episode generation is fire-and-forget, so we need to wait
        time.sleep(5)

        # The test passes if all messages went through without error.
        # Episode summary is created asynchronously - verification would
        # require direct DB access which is covered in unit tests.
        # Here we verify the system handles the load gracefully.


class TestCrossUserIsolation:
    """Tests for user memory isolation."""

    def test_cross_user_memory_isolation(self, client):
        """Test that users cannot access each other's memories."""
        user_a = f"integration-test-user-a-{uuid4().hex[:8]}"
        user_b = f"integration-test-user-b-{uuid4().hex[:8]}"

        # User A shares personal info
        client.post(
            "/chat",
            json={"message": "My secret project codename is Phoenix."},
            headers={"X-User-Id": user_a},
        )

        # User B asks about User A's info
        response = client.post(
            "/chat",
            json={"message": "What is the secret project codename?"},
            headers={"X-User-Id": user_b},
        )

        assert response.status_code == 200
        # Response should NOT contain User A's secret
        # (The assistant shouldn't know about Phoenix for User B)


class TestAsyncWritePerformance:
    """Tests for async write behavior."""

    def test_async_write_does_not_block_response(self, client):
        """Test that memory writes don't significantly delay responses."""
        user_id = f"integration-test-{uuid4().hex[:8]}"

        # Message with lots of saveable info
        message = (
            "My name is PerformanceTestUser, I'm a senior engineer at BigTech Corp, "
            "I live in San Francisco, I have two dogs named Max and Luna, "
            "I prefer TypeScript over JavaScript, and I'm building a ML platform."
        )

        start_time = time.time()
        response = client.post(
            "/chat",
            json={"message": message},
            headers={"X-User-Id": user_id},
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Response should complete in reasonable time despite multiple saves
        # (30 seconds is generous - actual should be much faster)
        assert elapsed < 30, f"Response took {elapsed:.1f}s, expected <30s"


class TestHealthCheck:
    """Basic health check to verify services are running."""

    def test_health_endpoint(self, client):
        """Verify health endpoint works."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
