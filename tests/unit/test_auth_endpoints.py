"""Unit tests for auth API endpoints (T021).

Tests /auth/status, /auth/setup, /auth/login, /auth/refresh, /auth/me
using FastAPI TestClient with mocked services.
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
def client():
    """Create a TestClient with lifespan dependencies mocked out.

    Patches database init, migrations, Redis, and memory-write drain
    so that the app lifespan completes without real infrastructure.
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
        from src.main import app
        with TestClient(app) as tc:
            yield tc


# ---------------------------------------------------------------------------
# GET /auth/status
# ---------------------------------------------------------------------------

class TestAuthStatus:
    """Tests for GET /auth/status."""

    def test_setup_required_when_no_users(self, client):
        with patch("src.api.auth.UserService") as MockUserService:
            instance = MockUserService.return_value
            instance.count_users = AsyncMock(return_value=0)

            response = client.get("/auth/status")

        assert response.status_code == 200
        assert response.json() == {"setup_required": True}

    def test_setup_not_required_when_users_exist(self, client):
        with patch("src.api.auth.UserService") as MockUserService:
            instance = MockUserService.return_value
            instance.count_users = AsyncMock(return_value=3)

            response = client.get("/auth/status")

        assert response.status_code == 200
        assert response.json() == {"setup_required": False}


# ---------------------------------------------------------------------------
# POST /auth/setup
# ---------------------------------------------------------------------------

class TestAuthSetup:
    """Tests for POST /auth/setup."""

    def test_creates_admin_when_no_users(self, client):
        admin_user = _make_user(username="admin", display_name="Admin", is_admin=True)

        with (
            patch("src.api.auth.UserService") as MockUserService,
            patch("src.api.auth.AuthService") as MockAuthService,
        ):
            user_svc = MockUserService.return_value
            user_svc.count_users = AsyncMock(return_value=0)
            user_svc.create_user = AsyncMock(return_value=admin_user)

            auth_svc = MockAuthService.return_value
            auth_svc.create_access_token = MagicMock(return_value="access-token-123")
            auth_svc.create_refresh_token = AsyncMock(
                return_value=("refresh-token-456", "hash-abc")
            )

            response = client.post(
                "/auth/setup",
                json={
                    "username": "admin",
                    "password": "strong-password-123",
                    "display_name": "Admin",
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["access_token"] == "access-token-123"
        assert body["refresh_token"] == "refresh-token-456"
        assert body["token_type"] == "bearer"
        assert body["user"]["username"] == "admin"
        assert body["user"]["is_admin"] is True

    def test_returns_409_when_users_exist(self, client):
        with patch("src.api.auth.UserService") as MockUserService:
            user_svc = MockUserService.return_value
            user_svc.count_users = AsyncMock(return_value=1)

            response = client.post(
                "/auth/setup",
                json={
                    "username": "admin",
                    "password": "strong-password-123",
                    "display_name": "Admin",
                },
            )

        assert response.status_code == 409
        assert "already" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

class TestAuthLogin:
    """Tests for POST /auth/login."""

    def test_login_valid_credentials(self, client):
        user = _make_user(username="alice", display_name="Alice")

        with (
            patch("src.api.auth.UserService") as MockUserService,
            patch("src.api.auth.AuthService") as MockAuthService,
        ):
            user_svc = MockUserService.return_value
            user_svc.get_by_username = AsyncMock(return_value=(user, "hashed-pw"))

            auth_svc = MockAuthService.return_value
            auth_svc.verify_password = MagicMock(return_value=True)
            auth_svc.create_access_token = MagicMock(return_value="jwt-access")
            auth_svc.create_refresh_token = AsyncMock(
                return_value=("jwt-refresh", "hash-xyz")
            )

            response = client.post(
                "/auth/login",
                json={"username": "alice", "password": "password-123"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["access_token"] == "jwt-access"
        assert body["refresh_token"] == "jwt-refresh"
        assert body["user"]["username"] == "alice"

    def test_login_wrong_password(self, client):
        user = _make_user(username="alice")

        with (
            patch("src.api.auth.UserService") as MockUserService,
            patch("src.api.auth.AuthService") as MockAuthService,
        ):
            user_svc = MockUserService.return_value
            user_svc.get_by_username = AsyncMock(return_value=(user, "hashed-pw"))

            auth_svc = MockAuthService.return_value
            auth_svc.verify_password = MagicMock(return_value=False)

            response = client.post(
                "/auth/login",
                json={"username": "alice", "password": "wrong-password"},
            )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_unknown_user(self, client):
        with patch("src.api.auth.UserService") as MockUserService:
            user_svc = MockUserService.return_value
            user_svc.get_by_username = AsyncMock(return_value=None)

            response = client.post(
                "/auth/login",
                json={"username": "ghost", "password": "password-123"},
            )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_disabled_user(self, client):
        user = _make_user(username="disabled_user", is_active=False)

        with (
            patch("src.api.auth.UserService") as MockUserService,
            patch("src.api.auth.AuthService") as MockAuthService,
        ):
            user_svc = MockUserService.return_value
            user_svc.get_by_username = AsyncMock(return_value=(user, "hashed-pw"))

            auth_svc = MockAuthService.return_value
            auth_svc.verify_password = MagicMock(return_value=True)

            response = client.post(
                "/auth/login",
                json={"username": "disabled_user", "password": "password-123"},
            )

        assert response.status_code == 401
        assert "disabled" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

class TestAuthRefresh:
    """Tests for POST /auth/refresh."""

    def test_refresh_valid_token(self, client):
        user = _make_user(username="alice")
        user_id = user.id

        with (
            patch("src.api.auth.AuthService") as MockAuthService,
            patch("src.api.auth.UserService") as MockUserService,
        ):
            auth_svc = MockAuthService.return_value
            auth_svc.validate_refresh_token = AsyncMock(return_value=user_id)
            auth_svc.rotate_refresh_token = AsyncMock(
                return_value=("new-refresh", "new-hash")
            )
            auth_svc.create_access_token = MagicMock(return_value="new-access-token")
            auth_svc.create_refresh_token = AsyncMock(
                return_value=("final-refresh", "final-hash")
            )

            user_svc = MockUserService.return_value
            user_svc.get_by_id = AsyncMock(return_value=user)

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "old-refresh-token"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["access_token"] == "new-access-token"
        assert body["refresh_token"] == "final-refresh"

    def test_refresh_invalid_token(self, client):
        with patch("src.api.auth.AuthService") as MockAuthService:
            auth_svc = MockAuthService.return_value
            auth_svc.validate_refresh_token = AsyncMock(return_value=None)

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "invalid-token"},
            )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_refresh_user_not_found(self, client):
        user_id = uuid4()

        with (
            patch("src.api.auth.AuthService") as MockAuthService,
            patch("src.api.auth.UserService") as MockUserService,
        ):
            auth_svc = MockAuthService.return_value
            auth_svc.validate_refresh_token = AsyncMock(return_value=user_id)

            user_svc = MockUserService.return_value
            user_svc.get_by_id = AsyncMock(return_value=None)

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "orphan-token"},
            )

        assert response.status_code == 401

    def test_refresh_disabled_user(self, client):
        user = _make_user(username="disabled", is_active=False)

        with (
            patch("src.api.auth.AuthService") as MockAuthService,
            patch("src.api.auth.UserService") as MockUserService,
        ):
            auth_svc = MockAuthService.return_value
            auth_svc.validate_refresh_token = AsyncMock(return_value=user.id)

            user_svc = MockUserService.return_value
            user_svc.get_by_id = AsyncMock(return_value=user)

            response = client.post(
                "/auth/refresh",
                json={"refresh_token": "disabled-user-token"},
            )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

class TestAuthMe:
    """Tests for GET /auth/me."""

    def test_returns_user_info_with_valid_token(self, client):
        user = _make_user(username="alice", display_name="Alice", is_admin=False)

        from src.api.dependencies import get_current_user
        from src.main import app

        app.dependency_overrides[get_current_user] = lambda: user
        try:
            response = client.get("/auth/me")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 200
        body = response.json()
        assert body["username"] == "alice"
        assert body["display_name"] == "Alice"
        assert body["is_admin"] is False
        assert body["is_active"] is True

    def test_returns_401_without_token(self, client):
        """When no Authorization header is sent, the endpoint rejects the request."""
        response = client.get("/auth/me")
        assert response.status_code in (401, 403)

    def test_returns_401_with_invalid_token(self, client):
        """Invalid Bearer token should be rejected by the dependency."""
        with (
            patch("src.api.dependencies.AuthService") as MockAuthService,
            patch("src.api.dependencies.UserService") as MockUserService,
        ):
            auth_svc = MockAuthService.return_value
            auth_svc.validate_access_token = MagicMock(
                side_effect=ValueError("Invalid access token")
            )

            response = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer invalid-jwt"},
            )

        assert response.status_code == 401
