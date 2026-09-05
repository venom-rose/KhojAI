"""Points of interest repository (Attraction, Activity, Hotel, Restaurant)."""

from typing import List, Optional, Sequence
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.travel.models.poi import Activity, Attraction, Hotel, Restaurant


class POIRepository:
    """Data access operations for POIs: Attractions, Activities, Hotels, Restaurants."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Attractions
    async def get_attraction_by_id(self, attraction_id: UUID) -> Optional[Attraction]:
        stmt = select(Attraction).where(Attraction.id == attraction_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_attractions_by_destination(
        self, destination_id: UUID, category: Optional[str] = None
    ) -> Sequence[Attraction]:
        stmt = select(Attraction).where(Attraction.destination_id == destination_id)
        if category:
            stmt = stmt.where(Attraction.category == category)
        stmt = stmt.order_by(Attraction.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_attraction(self, **kwargs) -> Attraction:
        attraction = Attraction(**kwargs)
        self.session.add(attraction)
        await self.session.flush()
        return attraction

    # Activities
    async def get_activity_by_id(self, activity_id: UUID) -> Optional[Activity]:
        stmt = select(Activity).where(Activity.id == activity_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_activities_by_destination(
        self, destination_id: UUID, activity_type: Optional[str] = None
    ) -> Sequence[Activity]:
        stmt = select(Activity).where(Activity.destination_id == destination_id)
        if activity_type:
            stmt = stmt.where(Activity.activity_type == activity_type)
        stmt = stmt.order_by(Activity.title)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_activity(self, **kwargs) -> Activity:
        activity = Activity(**kwargs)
        self.session.add(activity)
        await self.session.flush()
        return activity

    # Hotels
    async def get_hotel_by_id(self, hotel_id: UUID) -> Optional[Hotel]:
        stmt = select(Hotel).where(Hotel.id == hotel_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_hotels_by_destination(
        self,
        destination_id: UUID,
        stay_type: Optional[str] = None,
        price_level: Optional[str] = None,
    ) -> Sequence[Hotel]:
        stmt = select(Hotel).where(Hotel.destination_id == destination_id)
        if stay_type:
            stmt = stmt.where(Hotel.stay_type == stay_type)
        if price_level:
            stmt = stmt.where(Hotel.price_level == price_level)
        stmt = stmt.order_by(Hotel.rating.desc().nullslast(), Hotel.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_hotel(self, **kwargs) -> Hotel:
        hotel = Hotel(**kwargs)
        self.session.add(hotel)
        await self.session.flush()
        return hotel

    # Restaurants
    async def get_restaurant_by_id(self, restaurant_id: UUID) -> Optional[Restaurant]:
        stmt = select(Restaurant).where(Restaurant.id == restaurant_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_restaurants_by_destination(
        self, destination_id: UUID, cuisine_type: Optional[str] = None
    ) -> Sequence[Restaurant]:
        stmt = select(Restaurant).where(Restaurant.destination_id == destination_id)
        if cuisine_type:
            stmt = stmt.where(Restaurant.cuisine_type == cuisine_type)
        stmt = stmt.order_by(Restaurant.rating.desc().nullslast(), Restaurant.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_restaurant(self, **kwargs) -> Restaurant:
        restaurant = Restaurant(**kwargs)
        self.session.add(restaurant)
        await self.session.flush()
        return restaurant
