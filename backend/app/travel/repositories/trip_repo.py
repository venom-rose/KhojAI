"""Trip planning and user travel preference repository."""

import uuid
from typing import List, Optional, Sequence
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.travel.models.trip import Trip, TripDay, TripItem, UserTravelPreference


class TripRepository:
    """Data access operations for Trips, Days, Items, and Traveler Preferences."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Trip
    async def get_by_id(self, trip_id: UUID) -> Optional[Trip]:
        stmt = (
            select(Trip)
            .options(
                selectinload(Trip.days).selectinload(TripDay.items),
                selectinload(Trip.destination),
            )
            .where(Trip.id == trip_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_share_token(self, share_token: str) -> Optional[Trip]:
        stmt = (
            select(Trip)
            .options(
                selectinload(Trip.days).selectinload(TripDay.items),
                selectinload(Trip.destination),
            )
            .where(Trip.share_token == share_token)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_user(self, user_id: UUID, limit: int = 50, offset: int = 0) -> Sequence[Trip]:
        stmt = (
            select(Trip)
            .options(selectinload(Trip.days))
            .where(Trip.user_id == user_id)
            .order_by(Trip.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_trip(
        self,
        title: str,
        user_id: Optional[UUID] = None,
        destination_id: Optional[UUID] = None,
        total_days: int = 5,
        budget_tier: str = "₹₹",
        **kwargs,
    ) -> Trip:
        trip = Trip(
            user_id=user_id,
            destination_id=destination_id,
            title=title,
            total_days=total_days,
            budget_tier=budget_tier,
            **kwargs,
        )
        self.session.add(trip)
        await self.session.flush()
        return trip

    async def add_day(self, trip_id: UUID, day_number: int, theme_title: str, **kwargs) -> TripDay:
        day = TripDay(trip_id=trip_id, day_number=day_number, theme_title=theme_title, **kwargs)
        self.session.add(day)
        await self.session.flush()
        return day

    async def add_item(self, trip_day_id: UUID, item_type: str, title: str, sort_order: int = 1, **kwargs) -> TripItem:
        item = TripItem(trip_day_id=trip_day_id, item_type=item_type, title=title, sort_order=sort_order, **kwargs)
        self.session.add(item)
        await self.session.flush()
        return item

    # Preferences
    async def get_user_preference(self, user_id: UUID) -> Optional[UserTravelPreference]:
        stmt = select(UserTravelPreference).where(UserTravelPreference.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def upsert_user_preference(self, user_id: UUID, **kwargs) -> UserTravelPreference:
        pref = await self.get_user_preference(user_id)
        if not pref:
            pref = UserTravelPreference(user_id=user_id, **kwargs)
            self.session.add(pref)
        else:
            for k, v in kwargs.items():
                if v is not None:
                    setattr(pref, k, v)
        await self.session.flush()
        return pref
