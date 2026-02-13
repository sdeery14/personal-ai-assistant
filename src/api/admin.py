"""Admin API endpoints for user management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from src.api.dependencies import require_admin
from src.models.auth import CreateUserRequest, UpdateUserRequest, UserSummary
from src.models.user import User
from src.services.user_service import UserService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


def _user_summary(user: User) -> UserSummary:
    """Convert a User model to a UserSummary response."""
    return UserSummary(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        is_admin=user.is_admin,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/users")
async def list_users(
    admin: User = Depends(require_admin),
) -> list[UserSummary]:
    """List all users (admin only).

    Returns:
        List of UserSummary ordered by creation date
    """
    user_service = UserService()
    users = await user_service.list_users()
    return [_user_summary(u) for u in users]


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    admin: User = Depends(require_admin),
) -> UserSummary:
    """Create a new user (admin only).

    Args:
        request: New user details

    Returns:
        Created UserSummary

    Raises:
        HTTPException 409: If username already exists
    """
    user_service = UserService()

    # Check for duplicate username
    existing = await user_service.get_by_username(request.username)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{request.username}' already exists",
        )

    user = await user_service.create_user(
        username=request.username,
        password=request.password,
        display_name=request.display_name,
        is_admin=request.is_admin,
    )

    logger.info(
        "admin_created_user",
        admin_id=str(admin.id),
        new_user_id=str(user.id),
        new_username=user.username,
    )

    return _user_summary(user)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    admin: User = Depends(require_admin),
) -> UserSummary:
    """Update user details (admin only).

    Args:
        user_id: UUID of the user to update
        request: Fields to update

    Returns:
        Updated UserSummary

    Raises:
        HTTPException 404: If user not found
    """
    user_service = UserService()

    updated = await user_service.update_user(
        user_id=user_id,
        display_name=request.display_name,
        is_active=request.is_active,
        password=request.password,
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    logger.info(
        "admin_updated_user",
        admin_id=str(admin.id),
        target_user_id=str(user_id),
    )

    return _user_summary(updated)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
) -> None:
    """Delete a user (admin only).

    Admins cannot delete themselves to prevent lockout.

    Args:
        user_id: UUID of the user to delete

    Raises:
        HTTPException 403: If admin tries to delete themselves
        HTTPException 404: If user not found
    """
    if admin.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own admin account",
        )

    user_service = UserService()
    deleted = await user_service.delete_user(user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    logger.info(
        "admin_deleted_user",
        admin_id=str(admin.id),
        deleted_user_id=str(user_id),
    )
