"""Unit tests for notification API endpoints (T010).

Tests /notifications endpoints with mocked NotificationService
and dependency overrides for authentication.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.notification import Notification, NotificationType
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


def _make_notification(
    notification_id=None,
    user_id=None,
    message="Test notification",
    ntype=NotificationType.INFO,
    is_read=False,
    conversation_id=None,
):
    return Notification(
        id=notification_id or uuid4(),
        user_id=user_id or uuid4(),
        message=message,
        type=ntype,
        is_read=is_read,
        conversation_id=conversation_id,
        created_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def current_user():
    return _make_user(username="alice", display_name="Alice")


@pytest.fixture
def mock_service():
    """Create a fully-mocked NotificationService."""
    svc = MagicMock()
    svc.list_notifications = AsyncMock(return_value=([], 0))
    svc.get_unread_count = AsyncMock(return_value=0)
    svc.mark_as_read = AsyncMock(return_value=None)
    svc.mark_all_as_read = AsyncMock(return_value=0)
    svc.dismiss_notification = AsyncMock(return_value=False)
    return svc


@pytest.fixture
def client(current_user, mock_service):
    """Create a TestClient with lifespan mocked and auth overridden."""
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
# GET /notifications
# ---------------------------------------------------------------------------

class TestListNotifications:
    def test_returns_paginated_response(self, client, mock_service, current_user):
        n = _make_notification(user_id=current_user.id, message="Hello")
        mock_service.list_notifications.return_value = ([n], 1)

        response = client.get("/notifications")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["message"] == "Hello"
        assert body["items"][0]["type"] == "info"
        assert body["limit"] == 20
        assert body["offset"] == 0

    def test_type_filter_passed_to_service(self, client, mock_service):
        mock_service.list_notifications.return_value = ([], 0)

        response = client.get("/notifications?type=warning")

        assert response.status_code == 200
        call_kwargs = mock_service.list_notifications.call_args
        assert call_kwargs.kwargs.get("type_filter") == "warning" or \
            (len(call_kwargs.args) > 1 and call_kwargs.args[1] == "warning")

    def test_is_read_filter_passed_to_service(self, client, mock_service):
        mock_service.list_notifications.return_value = ([], 0)

        response = client.get("/notifications?is_read=false")

        assert response.status_code == 200
        call_kwargs = mock_service.list_notifications.call_args
        assert call_kwargs.kwargs.get("is_read_filter") is False or \
            (len(call_kwargs.args) > 2 and call_kwargs.args[2] is False)

    def test_returns_empty_list(self, client, mock_service):
        mock_service.list_notifications.return_value = ([], 0)

        response = client.get("/notifications")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0


# ---------------------------------------------------------------------------
# GET /notifications/unread-count
# ---------------------------------------------------------------------------

class TestUnreadCount:
    def test_returns_count(self, client, mock_service):
        mock_service.get_unread_count.return_value = 7

        response = client.get("/notifications/unread-count")

        assert response.status_code == 200
        assert response.json() == {"count": 7}

    def test_returns_zero_when_no_unread(self, client, mock_service):
        mock_service.get_unread_count.return_value = 0

        response = client.get("/notifications/unread-count")

        assert response.status_code == 200
        assert response.json() == {"count": 0}


# ---------------------------------------------------------------------------
# PATCH /notifications/{id}/read
# ---------------------------------------------------------------------------

class TestMarkAsRead:
    def test_returns_updated_notification(self, client, mock_service, current_user):
        n = _make_notification(user_id=current_user.id, is_read=True)
        mock_service.mark_as_read.return_value = n

        response = client.patch(f"/notifications/{n.id}/read")

        assert response.status_code == 200
        body = response.json()
        assert body["is_read"] is True
        assert body["id"] == str(n.id)

    def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.mark_as_read.return_value = None

        response = client.patch(f"/notifications/{uuid4()}/read")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /notifications/read-all
# ---------------------------------------------------------------------------

class TestMarkAllAsRead:
    def test_returns_updated_count(self, client, mock_service):
        mock_service.mark_all_as_read.return_value = 5

        response = client.patch("/notifications/read-all")

        assert response.status_code == 200
        assert response.json() == {"updated_count": 5}


# ---------------------------------------------------------------------------
# DELETE /notifications/{id}
# ---------------------------------------------------------------------------

class TestDismissNotification:
    def test_returns_204_on_success(self, client, mock_service):
        mock_service.dismiss_notification.return_value = True

        response = client.delete(f"/notifications/{uuid4()}")

        assert response.status_code == 204

    def test_returns_404_when_not_found(self, client, mock_service):
        mock_service.dismiss_notification.return_value = False

        response = client.delete(f"/notifications/{uuid4()}")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

class TestAuthRequired:
    def test_list_returns_401_without_token(self):
        """Endpoints require auth — no token means 401 Unauthorized."""
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

            # Clear any dependency overrides
            app.dependency_overrides.clear()

            with TestClient(app) as tc:
                response = tc.get("/notifications")
                assert response.status_code == 401
