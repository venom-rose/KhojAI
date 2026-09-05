from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.app.models import Contribution, Itinerary, Session, User
from backend.app.schemas.user import (
    TravelPreferencesIn,
    UserProfileOut,
    UserProfileUpdateIn,
    UserStatsOut,
)


class UserService:
    """Service handling profile retrieval, customization, preferences, and account deletion."""

    @staticmethod
    async def get_user_profile(db: AsyncSession, user: User) -> UserProfileOut:
        """Fetch user profile with aggregate statistics."""
        # Calculate saved itineraries count
        itineraries_count_result = await db.execute(
            select(func.count(Itinerary.id)).where(Itinerary.user_id == user.id)
        )
        saved_itineraries = itineraries_count_result.scalar_one_or_none() or 0

        # Calculate contributions count
        contributions_count_result = await db.execute(
            select(func.count(Contribution.id)).where(Contribution.user_id == user.id)
        )
        contributions = contributions_count_result.scalar_one_or_none() or 0

        stats = UserStatsOut(
            saved_itineraries_count=saved_itineraries,
            contributions_count=contributions,
        )

        return UserProfileOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            bio=user.bio,
            role=user.role,
            theme_preference=user.theme_preference or "light",
            travel_preferences=user.travel_preferences or {},
            is_active=user.is_active,
            is_verified=user.is_verified,
            stats=stats,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    async def update_user_profile(
        db: AsyncSession,
        user: User,
        payload: UserProfileUpdateIn,
    ) -> UserProfileOut:
        """Update personal profile details and theme preferences."""
        if payload.full_name is not None:
            user.full_name = payload.full_name.strip() if payload.full_name else None

        if payload.avatar_url is not None:
            user.avatar_url = payload.avatar_url.strip() if payload.avatar_url else None

        if payload.bio is not None:
            user.bio = payload.bio.strip() if payload.bio else None

        if payload.theme_preference is not None:
            user.theme_preference = payload.theme_preference

        await db.commit()
        await db.refresh(user)

        return await UserService.get_user_profile(db, user)

    @staticmethod
    async def update_travel_preferences(
        db: AsyncSession,
        user: User,
        payload: TravelPreferencesIn,
    ) -> UserProfileOut:
        """Update travel style and AI personalization preferences."""
        current_prefs = dict(user.travel_preferences or {})

        update_data = payload.model_dump(exclude_unset=True)
        current_prefs.update(update_data)

        user.travel_preferences = current_prefs
        flag_modified(user, "travel_preferences")

        await db.commit()
        await db.refresh(user)

        return await UserService.get_user_profile(db, user)

    @staticmethod
    async def delete_user_account(db: AsyncSession, user: User) -> bool:
        """Soft-delete user account and immediately revoke all active sessions."""
        user.soft_delete()
        user.is_active = False

        # Revoke all sessions for this user
        await db.execute(
            update(Session)
            .where(Session.user_id == user.id)
            .values(is_revoked=True)
        )

        await db.commit()
        return True


user_service = UserService()
