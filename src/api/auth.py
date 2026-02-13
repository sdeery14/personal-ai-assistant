"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from src.api.dependencies import get_current_user
from src.models.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    SetupRequest,
    UserSummary,
)
from src.models.user import User
from src.services.auth_service import ACCESS_TOKEN_EXPIRE_MINUTES, AuthService
from src.services.user_service import UserService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


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


async def _build_login_response(user: User) -> LoginResponse:
    """Create a LoginResponse with fresh access and refresh tokens."""
    auth_service = AuthService()
    access_token = auth_service.create_access_token(
        user_id=str(user.id),
        username=user.username,
        is_admin=user.is_admin,
    )
    raw_refresh, _ = await auth_service.create_refresh_token(user.id)

    return LoginResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_user_summary(user),
    )


@router.get("/status")
async def auth_status() -> dict:
    """Check if first-run setup is needed.

    Returns whether any users exist. Used by the frontend to decide
    whether to show the setup page or the login page.
    """
    user_service = UserService()
    count = await user_service.count_users()
    return {"setup_required": count == 0}


@router.post("/setup", status_code=status.HTTP_201_CREATED)
async def setup(request: SetupRequest) -> LoginResponse:
    """First-run admin account setup.

    Creates the initial admin account. Only works when no users exist.

    Args:
        request: Admin credentials and display name

    Returns:
        LoginResponse with tokens and user info

    Raises:
        HTTPException 409: If users already exist
    """
    user_service = UserService()
    count = await user_service.count_users()

    if count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup already completed. Users already exist.",
        )

    user = await user_service.create_user(
        username=request.username,
        password=request.password,
        display_name=request.display_name,
        is_admin=True,
    )

    logger.info("admin_setup_completed", user_id=str(user.id), username=user.username)
    return await _build_login_response(user)


@router.post("/login")
async def login(request: LoginRequest) -> LoginResponse:
    """Login with username and password.

    Args:
        request: Login credentials

    Returns:
        LoginResponse with tokens and user info

    Raises:
        HTTPException 401: If credentials are invalid or user is disabled
    """
    user_service = UserService()
    auth_service = AuthService()

    result = await user_service.get_by_username(request.username)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    user, password_hash = result

    if not auth_service.verify_password(request.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    logger.info("user_logged_in", user_id=str(user.id), username=user.username)
    return await _build_login_response(user)


@router.post("/refresh")
async def refresh(request: RefreshRequest) -> LoginResponse:
    """Refresh access token using a refresh token.

    Performs token rotation: the old refresh token is revoked and a new
    pair (access + refresh) is issued.

    Args:
        request: Refresh token to exchange

    Returns:
        LoginResponse with new tokens

    Raises:
        HTTPException 401: If refresh token is invalid, expired, or revoked
    """
    auth_service = AuthService()
    user_service = UserService()

    user_id = await auth_service.validate_refresh_token(request.refresh_token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await user_service.get_by_id(user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    # Rotate: revoke old, issue new
    await auth_service.rotate_refresh_token(request.refresh_token, user_id)

    # Build response with new tokens
    access_token = auth_service.create_access_token(
        user_id=str(user.id),
        username=user.username,
        is_admin=user.is_admin,
    )
    raw_refresh, _ = await auth_service.create_refresh_token(user.id)

    return LoginResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_user_summary(user),
    )


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)) -> UserSummary:
    """Get current authenticated user info.

    Args:
        current_user: User from JWT token

    Returns:
        UserSummary of the current user
    """
    return _user_summary(current_user)
