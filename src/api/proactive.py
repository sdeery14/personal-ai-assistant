"""Proactive API endpoints for Feature 011."""

import json

from fastapi import APIRouter, Depends
import structlog

from src.api.dependencies import get_current_user
from src.models.user import User
from src.services.proactive_service import ProactiveService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/proactive", tags=["Proactive"])


@router.get("/settings")
async def get_settings(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get proactiveness settings for the authenticated user."""
    service = ProactiveService()
    settings = await service.get_or_create_settings(str(current_user.id))

    suppressed = settings.get("suppressed_types", "[]")
    if isinstance(suppressed, str):
        suppressed = json.loads(suppressed)

    boosted = settings.get("boosted_types", "[]")
    if isinstance(boosted, str):
        boosted = json.loads(boosted)

    return {
        "global_level": settings["global_level"],
        "suppressed_types": suppressed,
        "boosted_types": boosted,
        "user_override": settings.get("user_override"),
        "is_onboarded": settings["is_onboarded"],
    }


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get aggregated user profile for the authenticated user."""
    service = ProactiveService()
    profile = await service.get_user_profile(str(current_user.id))
    return profile
