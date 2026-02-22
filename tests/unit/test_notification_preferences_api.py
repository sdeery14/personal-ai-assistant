"""Unit tests for notification preferences API endpoints (T025).

Tests GET/PUT /notifications/preferences with mocked NotificationService
and dependency overrides for authentication.
"""

from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.notification import (
    DeliveryChannel,
    NotificationPreferences,
)
from src.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(user_id=None, username="testuser", display_name="Test User"):
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        username=username,
        display_name=display_name,
        is_admin=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def current_user():
    return _make_user(username="alice", display_name="Alice")


@pytest.fixture
def mock_service():
    svc = MagicMock()
    svc.get_preferences = AsyncMock()
    svc.update_preferences = AsyncMock()
    return svc


@pytest.fixture
def client(current_user, mock_service):
    with (
        patch("src.database.init_database", new_callable=AsyncMock),
        patch("src.database.run_migrations", new_callable=AsyncMock),
        patch("src.services.redis_service.get_redis", new_callable=AsyncMock),
        patch("src.database.close_database", new_callable=AsyncMock),
        patch("src.services.redis_service.close_redis", new_callable=AsyncMock),
        patch("src.services.memory_write_service.await_pending_writes", new_callable=AsyncMock),
        patch("src.api.notifications.NotificationService", return_value=mock_service),
    ):
        from fastapi.testclient import TestClient
        from src.api.dependencies import get_current_user
        from src.main import app

        app.dependency_overrides[get_current_user] = lambda: current_user

        with TestClient(app) as tc:
            yield tc

        app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# GET /notifications/preferences
# ---------------------------------------------------------------------------

class TestGetPreferences:
    def test_returns_defaults_when_no_preferences(self, client, mock_service):
        mock_service.get_preferences.return_value = NotificationPreferences(
            delivery_channel=DeliveryChannel.IN_APP,
            quiet_hours_start=None,
            quiet_hours_end=None,
            quiet_hours_timezone="UTC",
        )

        response = client.get("/notifications/preferences")

        assert response.status_code == 200
        body = response.json()
        assert body["delivery_channel"] == "in_app"
        assert body["quiet_hours_start"] is None
        assert body["quiet_hours_end"] is None
        assert body["quiet_hours_timezone"] == "UTC"

    def test_returns_saved_preferences(self, client, mock_service):
        mock_service.get_preferences.return_value = NotificationPreferences(
            delivery_channel=DeliveryChannel.BOTH,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(7, 0),
            quiet_hours_timezone="America/New_York",
        )

        response = client.get("/notifications/preferences")

        assert response.status_code == 200
        body = response.json()
        assert body["delivery_channel"] == "both"
        assert body["quiet_hours_start"] == "22:00:00"
        assert body["quiet_hours_end"] == "07:00:00"
        assert body["quiet_hours_timezone"] == "America/New_York"


# ---------------------------------------------------------------------------
# PUT /notifications/preferences
# ---------------------------------------------------------------------------

class TestUpdatePreferences:
    def test_creates_preferences(self, client, mock_service):
        mock_service.update_preferences.return_value = NotificationPreferences(
            delivery_channel=DeliveryChannel.EMAIL,
            quiet_hours_start=None,
            quiet_hours_end=None,
            quiet_hours_timezone="UTC",
        )

        response = client.put(
            "/notifications/preferences",
            json={"delivery_channel": "email"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["delivery_channel"] == "email"

    def test_updates_with_quiet_hours(self, client, mock_service):
        mock_service.update_preferences.return_value = NotificationPreferences(
            delivery_channel=DeliveryChannel.BOTH,
            quiet_hours_start=time(23, 0),
            quiet_hours_end=time(8, 0),
            quiet_hours_timezone="America/Chicago",
        )

        response = client.put(
            "/notifications/preferences",
            json={
                "delivery_channel": "both",
                "quiet_hours_start": "23:00:00",
                "quiet_hours_end": "08:00:00",
                "quiet_hours_timezone": "America/Chicago",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["quiet_hours_start"] == "23:00:00"
        assert body["quiet_hours_end"] == "08:00:00"

    def test_rejects_partial_quiet_hours(self, client, mock_service):
        """quiet_hours_start and quiet_hours_end must both be set or both be null."""
        response = client.put(
            "/notifications/preferences",
            json={
                "delivery_channel": "both",
                "quiet_hours_start": "22:00:00",
                # quiet_hours_end is missing
            },
        )

        assert response.status_code == 422

    def test_validates_delivery_channel_enum(self, client, mock_service):
        response = client.put(
            "/notifications/preferences",
            json={"delivery_channel": "invalid_channel"},
        )

        # App uses custom validation handler that returns 400
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

class TestPreferencesAuthRequired:
    def test_get_preferences_requires_auth(self):
        with (
            patch("src.database.init_database", new_callable=AsyncMock),
            patch("src.database.run_migrations", new_callable=AsyncMock),
            patch("src.services.redis_service.get_redis", new_callable=AsyncMock),
            patch("src.database.close_database", new_callable=AsyncMock),
            patch("src.services.redis_service.close_redis", new_callable=AsyncMock),
            patch("src.services.memory_write_service.await_pending_writes", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from src.main import app

            app.dependency_overrides.clear()

            with TestClient(app) as tc:
                response = tc.get("/notifications/preferences")
                assert response.status_code == 401
