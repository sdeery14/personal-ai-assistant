"""FastAPI dependencies for authentication and authorization."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.models.user import User
from src.services.auth_service import AuthService
from src.services.user_service import UserService

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    """Extract and validate the current user from a JWT Bearer token.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        Authenticated User model

    Raises:
        HTTPException 401: If token is invalid, expired, or user not found/inactive
    """
    auth_service = AuthService()
    try:
        payload = auth_service.validate_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService()
    user = await user_service.get_by_id(UUID(user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the current user to have admin privileges.

    Args:
        current_user: Authenticated user from get_current_user

    Returns:
        Admin User model

    Raises:
        HTTPException 403: If user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
