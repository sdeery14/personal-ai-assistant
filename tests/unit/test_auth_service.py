"""Unit tests for AuthService (T019).

Tests JWT token creation/validation, bcrypt password hashing,
and refresh token lifecycle with mocked asyncpg database.
"""

import hashlib
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import jwt
import pytest

from src.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    AuthService,
)


# ---------------------------------------------------------------------------
# asyncpg mock helpers
# ---------------------------------------------------------------------------

class MockConnection:
    """Mock asyncpg connection with common query methods."""

    def __init__(self):
        self.execute = AsyncMock()
        self.fetchrow = AsyncMock()
        self.fetchval = AsyncMock()
        self.fetch = AsyncMock()


class MockPool:
    """Mock asyncpg pool with acquire() context manager."""

    def __init__(self, conn: MockConnection):
        self._conn = conn

    def acquire(self):
        return _MockPoolAcquire(self._conn)


class _MockPoolAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

JWT_SECRET = "test-secret-key-for-jwt-unit-tests"


@pytest.fixture
def auth_service():
    """Create an AuthService with a deterministic JWT secret."""
    with patch("src.services.auth_service.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(jwt_secret=JWT_SECRET)
        yield AuthService()


@pytest.fixture
def mock_pool():
    """Return (pool, connection) pair for database mocking."""
    conn = MockConnection()
    pool = MockPool(conn)
    return pool, conn


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    """Tests for bcrypt hash_password / verify_password."""

    def test_hash_password_returns_bcrypt_string(self, auth_service):
        hashed = auth_service.hash_password("my-secret-pw")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert len(hashed) == 60

    def test_hash_password_different_salts(self, auth_service):
        h1 = auth_service.hash_password("same-password")
        h2 = auth_service.hash_password("same-password")
        assert h1 != h2, "Each call should produce a unique salt"

    def test_verify_password_correct(self, auth_service):
        password = "correct-horse-battery"
        hashed = auth_service.hash_password(password)
        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_wrong(self, auth_service):
        hashed = auth_service.hash_password("right-password")
        assert auth_service.verify_password("wrong-password", hashed) is False


# ---------------------------------------------------------------------------
# Access tokens (JWT)
# ---------------------------------------------------------------------------

class TestAccessToken:
    """Tests for JWT access token creation and validation."""

    def test_create_access_token_returns_string(self, auth_service):
        token = auth_service.create_access_token(
            user_id="abc-123",
            username="testuser",
            is_admin=False,
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_and_validate_round_trip(self, auth_service):
        user_id = str(uuid4())
        token = auth_service.create_access_token(
            user_id=user_id,
            username="alice",
            is_admin=True,
        )
        payload = auth_service.validate_access_token(token)
        assert payload["sub"] == user_id
        assert payload["username"] == "alice"
        assert payload["is_admin"] is True

    def test_validate_access_token_contains_exp_and_iat(self, auth_service):
        token = auth_service.create_access_token(
            user_id="u1", username="bob", is_admin=False
        )
        payload = auth_service.validate_access_token(token)
        assert "exp" in payload
        assert "iat" in payload
        # exp should be ~15 minutes after iat
        delta = payload["exp"] - payload["iat"]
        assert delta == ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_validate_access_token_expired_raises(self, auth_service):
        """Manually craft an already-expired token and verify rejection."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user-1",
            "username": "expired_user",
            "is_admin": False,
            "iat": now - timedelta(hours=1),
            "exp": now - timedelta(minutes=1),
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

        with pytest.raises(ValueError, match="expired"):
            auth_service.validate_access_token(expired_token)

    def test_validate_access_token_tampered_raises(self, auth_service):
        """Sign with a different secret to simulate tampering."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user-1",
            "username": "hacker",
            "is_admin": True,
            "iat": now,
            "exp": now + timedelta(minutes=15),
        }
        tampered_token = jwt.encode(payload, "wrong-secret", algorithm=JWT_ALGORITHM)

        with pytest.raises(ValueError, match="Invalid"):
            auth_service.validate_access_token(tampered_token)

    def test_validate_access_token_garbage_string_raises(self, auth_service):
        with pytest.raises(ValueError, match="Invalid"):
            auth_service.validate_access_token("not.a.jwt.token")


# ---------------------------------------------------------------------------
# Refresh tokens (DB-backed)
# ---------------------------------------------------------------------------

class TestCreateRefreshToken:
    """Tests for create_refresh_token which stores hashed token in DB."""

    async def test_creates_token_and_inserts_row(self, auth_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()

        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            raw_token, token_hash = await auth_service.create_refresh_token(user_id)

        # Verify returned values
        assert isinstance(raw_token, str)
        assert len(raw_token) > 0
        assert token_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        # Verify INSERT was called
        conn.execute.assert_awaited_once()
        call_args = conn.execute.call_args
        sql = call_args[0][0]
        assert "INSERT INTO refresh_tokens" in sql
        # Second positional arg is user_id
        assert call_args[0][2] == user_id

    async def test_token_hash_is_sha256(self, auth_service, mock_pool):
        pool, _ = mock_pool
        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            raw_token, token_hash = await auth_service.create_refresh_token(uuid4())

        expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        assert token_hash == expected_hash

    async def test_each_call_produces_unique_token(self, auth_service, mock_pool):
        pool, _ = mock_pool
        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            t1, _ = await auth_service.create_refresh_token(uuid4())
            t2, _ = await auth_service.create_refresh_token(uuid4())

        assert t1 != t2


class TestValidateRefreshToken:
    """Tests for validate_refresh_token lookups."""

    async def test_valid_token_returns_user_id(self, auth_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        raw_token = "valid-refresh-token"

        conn.fetchrow.return_value = {
            "user_id": user_id,
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "revoked_at": None,
        }

        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            result = await auth_service.validate_refresh_token(raw_token)

        assert result == user_id

    async def test_unknown_token_returns_none(self, auth_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            result = await auth_service.validate_refresh_token("unknown-token")

        assert result is None

    async def test_revoked_token_returns_none(self, auth_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = {
            "user_id": uuid4(),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=1),
            "revoked_at": datetime.now(timezone.utc) - timedelta(hours=1),
        }

        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            result = await auth_service.validate_refresh_token("revoked-token")

        assert result is None

    async def test_expired_token_returns_none(self, auth_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = {
            "user_id": uuid4(),
            "expires_at": datetime.now(timezone.utc) - timedelta(hours=1),
            "revoked_at": None,
        }

        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            result = await auth_service.validate_refresh_token("expired-token")

        assert result is None


class TestRotateRefreshToken:
    """Tests for rotate_refresh_token (revoke old + create new)."""

    async def test_revokes_old_and_creates_new(self, auth_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        old_token = "old-refresh-token"

        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            new_raw, new_hash = await auth_service.rotate_refresh_token(old_token, user_id)

        # First call is the UPDATE (revoke old), second call is the INSERT (create new)
        assert conn.execute.await_count == 2

        # First call: revoke old token
        revoke_sql = conn.execute.call_args_list[0][0][0]
        assert "UPDATE refresh_tokens" in revoke_sql
        assert "revoked_at" in revoke_sql

        # Second call: insert new token
        insert_sql = conn.execute.call_args_list[1][0][0]
        assert "INSERT INTO refresh_tokens" in insert_sql

        # Verify new token is valid
        assert isinstance(new_raw, str)
        assert new_hash == hashlib.sha256(new_raw.encode("utf-8")).hexdigest()

    async def test_new_token_differs_from_old(self, auth_service, mock_pool):
        pool, _ = mock_pool
        old_token = "old-token-value"

        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            new_raw, _ = await auth_service.rotate_refresh_token(old_token, uuid4())

        assert new_raw != old_token


class TestRevokeAllUserTokens:
    """Tests for revoke_all_user_tokens."""

    async def test_updates_all_non_revoked_tokens(self, auth_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        conn.execute.return_value = "UPDATE 3"

        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            await auth_service.revoke_all_user_tokens(user_id)

        conn.execute.assert_awaited_once()
        call_args = conn.execute.call_args
        sql = call_args[0][0]
        assert "UPDATE refresh_tokens" in sql
        assert "revoked_at" in sql
        assert "user_id = $2" in sql
        assert "revoked_at IS NULL" in sql
        # user_id is the third positional arg (after sql and now)
        assert call_args[0][2] == user_id

    async def test_no_tokens_to_revoke(self, auth_service, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = "UPDATE 0"

        with patch("src.services.auth_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            # Should not raise
            await auth_service.revoke_all_user_tokens(uuid4())

        conn.execute.assert_awaited_once()
