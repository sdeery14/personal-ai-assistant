"""Unit tests for admin API endpoints (T022).

Tests /admin/users CRUD endpoints with mocked services
and dependency overrides for authentication.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin_user():
    """A pre-built admin user for dependency overrides."""
    return _make_user(
        username="admin",
        display_name="Admin",
        is_admin=True,
    )


@pytest.fixture
def non_admin_user():
    """A pre-built non-admin user for testing authorization."""
    return _make_user(
        username="regular",
        display_name="Regular User",
        is_admin=False,
    )


@pytest.fixture
def client(admin_user):
    """Create a TestClient with lifespan mocked and admin auth overridden.

    By default, all admin endpoints are authenticated as the admin_user.
    Individual tests can override or remove the dependency override.
    """
    with (
        patch("src.database.init_database", new_callable=AsyncMock),
        patch("src.database.run_migrations", new_callable=AsyncMock),
        patch("src.services.redis_service.get_redis", new_callable=AsyncMock),
        patch("src.database.close_database", new_callable=AsyncMock),
        patch("src.services.redis_service.close_redis", new_callable=AsyncMock),
        patch("src.services.memory_write_service.await_pending_writes", new_callable=AsyncMock),
    ):
        from fastapi.testclient import TestClient
        from src.api.dependencies import get_current_user, require_admin
        from src.main import app

        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[require_admin] = lambda: admin_user

        with TestClient(app) as tc:
            yield tc

        # Clean up overrides
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)


@pytest.fixture
def unauthenticated_client():
    """TestClient with NO auth overrides (no token)."""
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

        # Ensure no overrides leak from previous tests
        from src.api.dependencies import get_current_user, require_admin
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_admin, None)

        with TestClient(app) as tc:
            yield tc


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------

class TestListUsers:
    """Tests for GET /admin/users."""

    def test_returns_user_list_for_admin(self, client):
        users = [
            _make_user(username="alice", display_name="Alice", is_admin=True),
            _make_user(username="bob", display_name="Bob", is_admin=False),
        ]

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.list_users = AsyncMock(return_value=users)

            response = client.get("/admin/users")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["username"] == "alice"
        assert body[1]["username"] == "bob"

    def test_returns_empty_list_when_no_users(self, client):
        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.list_users = AsyncMock(return_value=[])

            response = client.get("/admin/users")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_403_for_non_admin(self, non_admin_user):
        """Non-admin users should be rejected by require_admin dependency."""
        with (
            patch("src.database.init_database", new_callable=AsyncMock),
            patch("src.database.run_migrations", new_callable=AsyncMock),
            patch("src.services.redis_service.get_redis", new_callable=AsyncMock),
            patch("src.database.close_database", new_callable=AsyncMock),
            patch("src.services.redis_service.close_redis", new_callable=AsyncMock),
            patch("src.services.memory_write_service.await_pending_writes", new_callable=AsyncMock),
        ):
            from fastapi.testclient import TestClient
            from src.api.dependencies import get_current_user, require_admin
            from fastapi import HTTPException, status
            from src.main import app

            app.dependency_overrides[get_current_user] = lambda: non_admin_user

            def _reject_non_admin():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required",
                )

            app.dependency_overrides[require_admin] = _reject_non_admin

            with TestClient(app) as tc:
                response = tc.get("/admin/users")

            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(require_admin, None)

        assert response.status_code == 403

    def test_returns_401_or_403_without_auth(self, unauthenticated_client):
        """No Authorization header should be rejected."""
        response = unauthenticated_client.get("/admin/users")
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /admin/users
# ---------------------------------------------------------------------------

class TestCreateUser:
    """Tests for POST /admin/users."""

    def test_creates_new_user(self, client):
        new_user = _make_user(
            username="newuser",
            display_name="New User",
            is_admin=False,
        )

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.get_by_username = AsyncMock(return_value=None)
            svc.create_user = AsyncMock(return_value=new_user)

            response = client.post(
                "/admin/users",
                json={
                    "username": "newuser",
                    "password": "strong-password-123",
                    "display_name": "New User",
                    "is_admin": False,
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["username"] == "newuser"
        assert body["display_name"] == "New User"
        assert body["is_admin"] is False

    def test_creates_admin_user(self, client):
        new_admin = _make_user(
            username="newadmin",
            display_name="New Admin",
            is_admin=True,
        )

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.get_by_username = AsyncMock(return_value=None)
            svc.create_user = AsyncMock(return_value=new_admin)

            response = client.post(
                "/admin/users",
                json={
                    "username": "newadmin",
                    "password": "admin-password-123",
                    "display_name": "New Admin",
                    "is_admin": True,
                },
            )

        assert response.status_code == 201
        assert response.json()["is_admin"] is True

    def test_returns_409_for_duplicate_username(self, client):
        existing = _make_user(username="taken")

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.get_by_username = AsyncMock(return_value=(existing, "hashed-pw"))

            response = client.post(
                "/admin/users",
                json={
                    "username": "taken",
                    "password": "strong-password-123",
                    "display_name": "Duplicate",
                },
            )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


# ---------------------------------------------------------------------------
# PATCH /admin/users/{user_id}
# ---------------------------------------------------------------------------

class TestUpdateUser:
    """Tests for PATCH /admin/users/{user_id}."""

    def test_updates_user_fields(self, client):
        user_id = uuid4()
        updated = _make_user(
            user_id=user_id,
            username="alice",
            display_name="Alice Updated",
            is_active=False,
        )

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.update_user = AsyncMock(return_value=updated)

            response = client.patch(
                f"/admin/users/{user_id}",
                json={"display_name": "Alice Updated", "is_active": False},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["display_name"] == "Alice Updated"
        assert body["is_active"] is False

    def test_updates_password_only(self, client):
        user_id = uuid4()
        updated = _make_user(user_id=user_id, username="alice")

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.update_user = AsyncMock(return_value=updated)

            response = client.patch(
                f"/admin/users/{user_id}",
                json={"password": "new-strong-password"},
            )

        assert response.status_code == 200

    def test_returns_404_for_unknown_user(self, client):
        unknown_id = uuid4()

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.update_user = AsyncMock(return_value=None)

            response = client.patch(
                f"/admin/users/{unknown_id}",
                json={"display_name": "Ghost"},
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_empty_update_body_succeeds(self, client):
        user_id = uuid4()
        existing = _make_user(user_id=user_id, username="alice")

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.update_user = AsyncMock(return_value=existing)

            response = client.patch(
                f"/admin/users/{user_id}",
                json={},
            )

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# DELETE /admin/users/{user_id}
# ---------------------------------------------------------------------------

class TestDeleteUser:
    """Tests for DELETE /admin/users/{user_id}."""

    def test_deletes_user(self, client):
        target_id = uuid4()

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.delete_user = AsyncMock(return_value=True)

            response = client.delete(f"/admin/users/{target_id}")

        assert response.status_code == 204

    def test_returns_403_when_deleting_self(self, client, admin_user):
        """Admin should not be able to delete their own account."""
        response = client.delete(f"/admin/users/{admin_user.id}")
        assert response.status_code == 403
        assert "own admin account" in response.json()["detail"].lower()

    def test_returns_404_for_unknown_user(self, client):
        unknown_id = uuid4()

        with patch("src.api.admin.UserService") as MockUserService:
            svc = MockUserService.return_value
            svc.delete_user = AsyncMock(return_value=False)

            response = client.delete(f"/admin/users/{unknown_id}")

        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_delete_without_auth_returns_401_or_403(self, unauthenticated_client):
        """No Authorization header should be rejected."""
        target_id = uuid4()
        response = unauthenticated_client.delete(f"/admin/users/{target_id}")
        assert response.status_code in (401, 403)
