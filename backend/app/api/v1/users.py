from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user
from backend.app.config.settings import settings
from backend.app.database.session import get_db
from backend.app.models import User
from backend.app.schemas.auth import MessageResponse
from backend.app.schemas.user import (
    TravelPreferencesIn,
    UserProfileOut,
    UserProfileUpdateIn,
)
from backend.app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["Users & Profile"])


@router.get(
    "/me",
    response_model=UserProfileOut,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user profile",
    description="Fetch current user's profile, theme settings, travel preferences, and activity statistics.",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileOut:
    return await user_service.get_user_profile(db=db, user=current_user)


@router.patch(
    "/me",
    response_model=UserProfileOut,
    status_code=status.HTTP_200_OK,
    summary="Update profile details and theme",
    description="Modify personal details (full_name, avatar_url, bio) and visual theme preference.",
)
async def update_my_profile(
    payload: UserProfileUpdateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileOut:
    return await user_service.update_user_profile(
        db=db,
        user=current_user,
        payload=payload,
    )


@router.patch(
    "/me/preferences",
    response_model=UserProfileOut,
    status_code=status.HTTP_200_OK,
    summary="Update travel and AI preferences",
    description="Customize travel pacing, default trip duration, budget tier, party size, and favorite interest tags.",
)
async def update_my_preferences(
    payload: TravelPreferencesIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileOut:
    return await user_service.update_travel_preferences(
        db=db,
        user=current_user,
        payload=payload,
    )


@router.delete(
    "/me",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete account",
    description="Soft-delete user account, revoke active sessions, and clear authentication cookies.",
)
async def delete_my_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await user_service.delete_user_account(db=db, user=current_user)

    # Clear authentication cookie
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAME_SITE,
    )

    return MessageResponse(
        ok=True,
        message="Your account has been deleted successfully.",
    )
