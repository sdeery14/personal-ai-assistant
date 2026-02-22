"""User management service."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog

from src.database import get_pool
from src.models.user import User
from src.services.auth_service import AuthService

logger = structlog.get_logger(__name__)


class UserService:
    """Service for user CRUD operations."""

    def __init__(self):
        self.auth_service = AuthService()

    async def create_user(
        self,
        username: str,
        password: str,
        display_name: str,
        is_admin: bool = False,
    ) -> User:
        """Create a new user with a hashed password.

        Args:
            username: Unique username
            password: Plain-text password (will be hashed)
            display_name: User's display name
            is_admin: Whether the user has admin privileges

        Returns:
            Created User model

        Raises:
            RuntimeError: If the database insert fails
        """
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        password_hash = self.auth_service.hash_password(password)

        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, username, password_hash, display_name, is_admin, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, TRUE, $6, $7)
                """,
                user_id,
                username,
                password_hash,
                display_name,
                is_admin,
                now,
                now,
            )

        logger.info(
            "user_created",
            user_id=str(user_id),
            username=username,
            is_admin=is_admin,
        )

        return User(
            id=user_id,
            username=username,
            display_name=display_name,
            is_admin=is_admin,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    async def get_by_username(self, username: str) -> Optional[tuple[User, str]]:
        """Get a user by username (case-insensitive).

        Args:
            username: Username to look up

        Returns:
            Tuple of (User, password_hash) or None if not found
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, username, password_hash, display_name, is_admin, is_active, created_at, updated_at
                FROM users
                WHERE LOWER(username) = LOWER($1)
                """,
                username,
            )

        if row is None:
            return None

        user = User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            is_admin=row["is_admin"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        return user, row["password_hash"]

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by UUID.

        Args:
            user_id: User UUID

        Returns:
            User model or None if not found
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, username, display_name, is_admin, is_active, created_at, updated_at
                FROM users
                WHERE id = $1
                """,
                user_id,
            )

        if row is None:
            return None

        return User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            is_admin=row["is_admin"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def list_users(self) -> list[User]:
        """Return all users ordered by creation date.

        Returns:
            List of User models ordered by created_at ascending
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, username, display_name, is_admin, is_active, created_at, updated_at
                FROM users
                ORDER BY created_at ASC
                """
            )

        return [
            User(
                id=row["id"],
                username=row["username"],
                display_name=row["display_name"],
                is_admin=row["is_admin"],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def get_email(self, user_id: UUID) -> Optional[str]:
        """Get the email address for a user.

        Args:
            user_id: User UUID

        Returns:
            Email string or None if not set
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT email FROM users WHERE id = $1",
                user_id,
            )

    async def update_user(
        self,
        user_id: UUID,
        display_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        password: Optional[str] = None,
        email: Optional[str] = None,
    ) -> Optional[User]:
        """Update user fields that are not None.

        Args:
            user_id: UUID of the user to update
            display_name: New display name (if provided)
            is_active: New active status (if provided)
            password: New plain-text password (if provided, will be hashed)

        Returns:
            Updated User model, or None if user not found
        """
        # Build SET clause dynamically for non-None fields
        set_clauses = []
        params = []
        param_idx = 1

        if display_name is not None:
            set_clauses.append(f"display_name = ${param_idx}")
            params.append(display_name)
            param_idx += 1

        if is_active is not None:
            set_clauses.append(f"is_active = ${param_idx}")
            params.append(is_active)
            param_idx += 1

        if password is not None:
            password_hash = self.auth_service.hash_password(password)
            set_clauses.append(f"password_hash = ${param_idx}")
            params.append(password_hash)
            param_idx += 1

        if email is not None:
            set_clauses.append(f"email = ${param_idx}")
            params.append(email)
            param_idx += 1

        if not set_clauses:
            # Nothing to update; just return the current user
            return await self.get_by_id(user_id)

        # Always update updated_at
        now = datetime.now(timezone.utc)
        set_clauses.append(f"updated_at = ${param_idx}")
        params.append(now)
        param_idx += 1

        # Add user_id as the final parameter for the WHERE clause
        params.append(user_id)

        query = f"""
            UPDATE users
            SET {', '.join(set_clauses)}
            WHERE id = ${param_idx}
            RETURNING id, username, display_name, is_admin, is_active, created_at, updated_at
        """

        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if row is None:
            return None

        logger.info(
            "user_updated",
            user_id=str(user_id),
            fields_updated=[c.split(" = ")[0] for c in set_clauses if "updated_at" not in c],
        )

        return User(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            is_admin=row["is_admin"],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def delete_user(self, user_id: UUID) -> bool:
        """Hard-delete a user from the database.

        Args:
            user_id: UUID of the user to delete

        Returns:
            True if the user was deleted, False if not found
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM users WHERE id = $1
                """,
                user_id,
            )

        deleted = result == "DELETE 1"

        if deleted:
            logger.info("user_deleted", user_id=str(user_id))
        else:
            logger.warning("user_delete_not_found", user_id=str(user_id))

        return deleted

    async def count_users(self) -> int:
        """Count total number of users.

        Returns:
            Total user count
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM users")

        return count

    async def count_admins(self) -> int:
        """Count number of admin users.

        Returns:
            Admin user count
        """
        pool = await get_pool()

        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE is_admin = TRUE"
            )

        return count
