"""User and authentication models."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    """A registered user of the assistant."""

    id: UUID
    username: str
    display_name: str
    email: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class RefreshToken(BaseModel):
    """A refresh token for JWT rotation."""

    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    created_at: datetime
