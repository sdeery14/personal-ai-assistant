"""Auth request and response models with validation."""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    """Login credentials for authentication.

    Attributes:
        username: User's unique identifier (3-100 chars, alphanumeric + underscore/hyphen)
        password: User's password (min 8 chars)
    """

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def username_valid_chars(cls, v: str) -> str:
        """Ensure username contains only alphanumeric, underscore, or hyphen."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Username must contain only alphanumeric characters, "
                "underscores, or hyphens"
            )
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        """Ensure password is not empty or whitespace only."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Password cannot be empty or whitespace only")
        return v


class UserSummary(BaseModel):
    """Compact user representation for API responses."""

    id: UUID
    username: str
    display_name: str
    is_admin: bool
    is_active: bool
    created_at: datetime


class LoginResponse(BaseModel):
    """Successful authentication response with token pair.

    Attributes:
        access_token: Short-lived JWT for API access
        refresh_token: Long-lived token for obtaining new access tokens
        token_type: Always "bearer"
        expires_in: Access token lifetime in seconds
        user: Summary of the authenticated user
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(ge=1, description="Access token lifetime in seconds")
    user: UserSummary


class SetupRequest(BaseModel):
    """Initial admin account setup request.

    Attributes:
        username: Admin username (3-100 chars, alphanumeric + underscore/hyphen)
        password: Admin password (min 8 chars)
        display_name: Human-readable display name (max 255 chars)
    """

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., max_length=255)

    @field_validator("username")
    @classmethod
    def username_valid_chars(cls, v: str) -> str:
        """Ensure username contains only alphanumeric, underscore, or hyphen."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Username must contain only alphanumeric characters, "
                "underscores, or hyphens"
            )
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        """Ensure password is not empty or whitespace only."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Password cannot be empty or whitespace only")
        return v


class RefreshRequest(BaseModel):
    """Request to exchange a refresh token for a new token pair.

    Attributes:
        refresh_token: The refresh token to exchange
    """

    refresh_token: str


class CreateUserRequest(BaseModel):
    """Admin request to create a new user.

    Attributes:
        username: New user's identifier (3-100 chars, alphanumeric + underscore/hyphen)
        password: New user's password (min 8 chars)
        display_name: Human-readable display name (max 255 chars)
        is_admin: Whether the new user has admin privileges
    """

    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., max_length=255)
    is_admin: bool = False

    @field_validator("username")
    @classmethod
    def username_valid_chars(cls, v: str) -> str:
        """Ensure username contains only alphanumeric, underscore, or hyphen."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                "Username must contain only alphanumeric characters, "
                "underscores, or hyphens"
            )
        return v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        """Ensure password is not empty or whitespace only."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Password cannot be empty or whitespace only")
        return v


class UpdateUserRequest(BaseModel):
    """Request to update an existing user's details.

    All fields are optional; only provided fields are updated.

    Attributes:
        display_name: New display name (max 255 chars)
        is_active: Enable or disable the user account
        password: New password (min 8 chars if provided)
    """

    display_name: Optional[str] = Field(default=None, max_length=255)
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8)

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Ensure password is not empty or whitespace only when provided."""
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Password cannot be empty or whitespace only")
        return v
