"""Authentication service for JWT tokens and password hashing."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import bcrypt
import jwt
import structlog

from src.config import get_settings
from src.database import get_pool

logger = structlog.get_logger(__name__)

# Constants
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthService:
    """Service for authentication, JWT management, and refresh token lifecycle."""

    def __init__(self):
        self.settings = get_settings()

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain-text password to hash

        Returns:
            Bcrypt hash string
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against a bcrypt hash.

        Args:
            password: Plain-text password to check
            password_hash: Bcrypt hash to verify against

        Returns:
            True if the password matches, False otherwise
        """
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )

    def create_access_token(
        self, user_id: str, username: str, is_admin: bool
    ) -> str:
        """Create a signed JWT access token.

        Args:
            user_id: User UUID as string (placed in 'sub' claim)
            username: Username to include in payload
            is_admin: Whether the user has admin privileges

        Returns:
            Encoded JWT string
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "username": username,
            "is_admin": is_admin,
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        token = jwt.encode(payload, self.settings.jwt_secret, algorithm=JWT_ALGORITHM)
        logger.debug(
            "access_token_created",
            user_id=user_id,
            username=username,
            expires_minutes=ACCESS_TOKEN_EXPIRE_MINUTES,
        )
        return token

    def validate_access_token(self, token: str) -> dict:
        """Decode and validate a JWT access token.

        Args:
            token: Encoded JWT string

        Returns:
            Decoded payload dict with sub, username, is_admin, iat, exp

        Raises:
            ValueError: If the token is invalid, expired, or malformed
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret,
                algorithms=[JWT_ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Access token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid access token: {e}")

    async def create_refresh_token(self, user_id: UUID) -> tuple[str, str]:
        """Generate a refresh token, hash it, and store in the database.

        Args:
            user_id: User UUID to associate the token with

        Returns:
            Tuple of (raw_token, token_hash)
        """
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        token_id = uuid4()
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, created_at)
                VALUES ($1, $2, $3, $4, $5)
                """,
                token_id,
                user_id,
                token_hash,
                expires_at,
                now,
            )

        logger.info(
            "refresh_token_created",
            user_id=str(user_id),
            token_id=str(token_id),
            expires_at=expires_at.isoformat(),
        )

        return raw_token, token_hash

    async def validate_refresh_token(self, raw_token: str) -> Optional[UUID]:
        """Validate a refresh token by hashing and looking up in the database.

        Args:
            raw_token: The raw (unhashed) refresh token string

        Returns:
            The user_id if the token is valid, not revoked, and not expired;
            None otherwise
        """
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc)

        pool = await get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT user_id, expires_at, revoked_at
                FROM refresh_tokens
                WHERE token_hash = $1
                """,
                token_hash,
            )

        if row is None:
            logger.warning("refresh_token_not_found")
            return None

        if row["revoked_at"] is not None:
            logger.warning(
                "refresh_token_revoked",
                user_id=str(row["user_id"]),
            )
            return None

        if row["expires_at"] < now:
            logger.warning(
                "refresh_token_expired",
                user_id=str(row["user_id"]),
            )
            return None

        return row["user_id"]

    async def rotate_refresh_token(
        self, old_token: str, user_id: UUID
    ) -> tuple[str, str]:
        """Revoke the old refresh token and create a new one.

        Args:
            old_token: The raw old refresh token to revoke
            user_id: User UUID for the new token

        Returns:
            Tuple of (new_raw_token, new_token_hash)
        """
        old_hash = hashlib.sha256(old_token.encode("utf-8")).hexdigest()
        now = datetime.now(timezone.utc)

        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = $1
                WHERE token_hash = $2 AND revoked_at IS NULL
                """,
                now,
                old_hash,
            )

        logger.info(
            "refresh_token_revoked",
            user_id=str(user_id),
        )

        new_raw_token, new_hash = await self.create_refresh_token(user_id)
        return new_raw_token, new_hash

    async def revoke_all_user_tokens(self, user_id: UUID) -> None:
        """Revoke all refresh tokens for a user.

        Args:
            user_id: User UUID whose tokens should be revoked
        """
        now = datetime.now(timezone.utc)

        pool = await get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE refresh_tokens
                SET revoked_at = $1
                WHERE user_id = $2 AND revoked_at IS NULL
                """,
                now,
                user_id,
            )

        logger.info(
            "all_refresh_tokens_revoked",
            user_id=str(user_id),
            result=result,
        )
