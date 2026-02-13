"""Unit tests for UserService (T020).

Tests user CRUD operations with mocked asyncpg database.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.models.user import User
from src.services.user_service import UserService


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

@pytest.fixture
def mock_pool():
    """Return (pool, connection) pair for database mocking."""
    conn = MockConnection()
    pool = MockPool(conn)
    return pool, conn


@pytest.fixture
def user_service():
    """Create a UserService with mocked settings (for AuthService inside)."""
    with patch("src.services.auth_service.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(jwt_secret="test-secret")
        yield UserService()


def _make_user_row(
    user_id=None,
    username="testuser",
    password_hash="$2b$12$hashedpasswordhere000000000000000000000000000000000000",
    display_name="Test User",
    is_admin=False,
    is_active=True,
    created_at=None,
    updated_at=None,
):
    """Create a dict that mimics an asyncpg Record for a users row."""
    now = datetime.now(timezone.utc)
    return {
        "id": user_id or uuid4(),
        "username": username,
        "password_hash": password_hash,
        "display_name": display_name,
        "is_admin": is_admin,
        "is_active": is_active,
        "created_at": created_at or now,
        "updated_at": updated_at or now,
    }


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

class TestCreateUser:
    """Tests for UserService.create_user."""

    async def test_inserts_row_and_returns_user(self, user_service, mock_pool):
        pool, conn = mock_pool

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.create_user(
                username="alice",
                password="strong-password-123",
                display_name="Alice Smith",
                is_admin=False,
            )

        assert isinstance(user, User)
        assert user.username == "alice"
        assert user.display_name == "Alice Smith"
        assert user.is_admin is False
        assert user.is_active is True
        assert isinstance(user.id, UUID)
        assert isinstance(user.created_at, datetime)
        assert user.created_at == user.updated_at

        # Verify INSERT was issued
        conn.execute.assert_awaited_once()
        sql = conn.execute.call_args[0][0]
        assert "INSERT INTO users" in sql

    async def test_creates_admin_user(self, user_service, mock_pool):
        pool, conn = mock_pool

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.create_user(
                username="admin",
                password="admin-password-123",
                display_name="Admin",
                is_admin=True,
            )

        assert user.is_admin is True

    async def test_password_is_hashed_not_plaintext(self, user_service, mock_pool):
        pool, conn = mock_pool
        plaintext = "my-secret-password"

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            await user_service.create_user(
                username="bob",
                password=plaintext,
                display_name="Bob",
            )

        # The third positional arg in the INSERT is password_hash
        insert_args = conn.execute.call_args[0]
        stored_hash = insert_args[3]  # $3 = password_hash
        assert stored_hash != plaintext
        assert stored_hash.startswith("$2b$") or stored_hash.startswith("$2a$")


# ---------------------------------------------------------------------------
# get_by_username
# ---------------------------------------------------------------------------

class TestGetByUsername:
    """Tests for UserService.get_by_username."""

    async def test_returns_user_and_hash_when_found(self, user_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        password_hash = "$2b$12$somehashedvalue"

        conn.fetchrow.return_value = _make_user_row(
            user_id=user_id,
            username="alice",
            password_hash=password_hash,
            display_name="Alice",
            is_admin=False,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            result = await user_service.get_by_username("alice")

        assert result is not None
        user, pw_hash = result
        assert isinstance(user, User)
        assert user.username == "alice"
        assert user.id == user_id
        assert pw_hash == password_hash

    async def test_returns_none_when_not_found(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            result = await user_service.get_by_username("nonexistent")

        assert result is None

    async def test_query_uses_case_insensitive_match(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            await user_service.get_by_username("Alice")

        sql = conn.fetchrow.call_args[0][0]
        assert "LOWER(username) = LOWER($1)" in sql


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

class TestGetById:
    """Tests for UserService.get_by_id."""

    async def test_returns_user_when_found(self, user_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        row = _make_user_row(user_id=user_id, username="bob", created_at=now, updated_at=now)
        # get_by_id query doesn't select password_hash
        del row["password_hash"]
        conn.fetchrow.return_value = row

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.get_by_id(user_id)

        assert user is not None
        assert user.id == user_id
        assert user.username == "bob"

    async def test_returns_none_when_not_found(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.get_by_id(uuid4())

        assert user is None


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

class TestListUsers:
    """Tests for UserService.list_users."""

    async def test_returns_list_of_users(self, user_service, mock_pool):
        pool, conn = mock_pool
        now = datetime.now(timezone.utc)

        rows = [
            {
                "id": uuid4(),
                "username": "alice",
                "display_name": "Alice",
                "is_admin": True,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": uuid4(),
                "username": "bob",
                "display_name": "Bob",
                "is_admin": False,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        ]
        conn.fetch.return_value = rows

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            users = await user_service.list_users()

        assert len(users) == 2
        assert all(isinstance(u, User) for u in users)
        assert users[0].username == "alice"
        assert users[1].username == "bob"

    async def test_returns_empty_list_when_no_users(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = []

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            users = await user_service.list_users()

        assert users == []

    async def test_query_orders_by_created_at(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetch.return_value = []

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            await user_service.list_users()

        sql = conn.fetch.call_args[0][0]
        assert "ORDER BY created_at ASC" in sql


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

class TestUpdateUser:
    """Tests for UserService.update_user."""

    async def test_update_display_name(self, user_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        conn.fetchrow.return_value = {
            "id": user_id,
            "username": "alice",
            "display_name": "Alice Updated",
            "is_admin": False,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.update_user(user_id, display_name="Alice Updated")

        assert user is not None
        assert user.display_name == "Alice Updated"
        sql = conn.fetchrow.call_args[0][0]
        assert "display_name" in sql
        assert "RETURNING" in sql

    async def test_update_is_active(self, user_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        conn.fetchrow.return_value = {
            "id": user_id,
            "username": "alice",
            "display_name": "Alice",
            "is_admin": False,
            "is_active": False,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.update_user(user_id, is_active=False)

        assert user is not None
        assert user.is_active is False
        sql = conn.fetchrow.call_args[0][0]
        assert "is_active" in sql

    async def test_update_password(self, user_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        conn.fetchrow.return_value = {
            "id": user_id,
            "username": "alice",
            "display_name": "Alice",
            "is_admin": False,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.update_user(user_id, password="new-password-123")

        assert user is not None
        sql = conn.fetchrow.call_args[0][0]
        assert "password_hash" in sql

    async def test_update_multiple_fields(self, user_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        conn.fetchrow.return_value = {
            "id": user_id,
            "username": "alice",
            "display_name": "New Name",
            "is_admin": False,
            "is_active": False,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.update_user(
                user_id,
                display_name="New Name",
                is_active=False,
                password="changed-pw-456",
            )

        assert user is not None
        sql = conn.fetchrow.call_args[0][0]
        assert "display_name" in sql
        assert "is_active" in sql
        assert "password_hash" in sql
        assert "updated_at" in sql

    async def test_update_no_fields_returns_existing(self, user_service, mock_pool):
        """When no fields are provided, get_by_id is called instead of UPDATE."""
        pool, conn = mock_pool
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        # Mock for get_by_id (called when no fields to update)
        conn.fetchrow.return_value = {
            "id": user_id,
            "username": "alice",
            "display_name": "Alice",
            "is_admin": False,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.update_user(user_id)

        assert user is not None
        assert user.username == "alice"
        # The SQL should be a SELECT (get_by_id), not an UPDATE
        sql = conn.fetchrow.call_args[0][0]
        assert "SELECT" in sql
        assert "UPDATE" not in sql

    async def test_update_nonexistent_user_returns_none(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchrow.return_value = None

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            user = await user_service.update_user(uuid4(), display_name="Ghost")

        assert user is None


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------

class TestDeleteUser:
    """Tests for UserService.delete_user."""

    async def test_returns_true_when_deleted(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = "DELETE 1"

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            result = await user_service.delete_user(uuid4())

        assert result is True

    async def test_returns_false_when_not_found(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.execute.return_value = "DELETE 0"

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            result = await user_service.delete_user(uuid4())

        assert result is False

    async def test_issues_delete_sql(self, user_service, mock_pool):
        pool, conn = mock_pool
        user_id = uuid4()
        conn.execute.return_value = "DELETE 1"

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            await user_service.delete_user(user_id)

        sql = conn.execute.call_args[0][0]
        assert "DELETE FROM users" in sql
        assert conn.execute.call_args[0][1] == user_id


# ---------------------------------------------------------------------------
# count_users / count_admins
# ---------------------------------------------------------------------------

class TestCountUsers:
    """Tests for UserService.count_users."""

    async def test_returns_count(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = 5

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            count = await user_service.count_users()

        assert count == 5

    async def test_returns_zero_when_empty(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = 0

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            count = await user_service.count_users()

        assert count == 0


class TestCountAdmins:
    """Tests for UserService.count_admins."""

    async def test_returns_admin_count(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = 2

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            count = await user_service.count_admins()

        assert count == 2

    async def test_query_filters_by_admin(self, user_service, mock_pool):
        pool, conn = mock_pool
        conn.fetchval.return_value = 0

        with patch("src.services.user_service.get_pool", new_callable=AsyncMock) as mock_get_pool:
            mock_get_pool.return_value = pool
            await user_service.count_admins()

        sql = conn.fetchval.call_args[0][0]
        assert "is_admin = TRUE" in sql
