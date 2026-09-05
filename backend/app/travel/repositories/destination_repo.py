"""Destination and Geography Repository for KHOJAI Travel Intelligence."""

from typing import List, Optional, Sequence
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.destination import Destination
from backend.app.travel.models.destination import DestinationCategory, Season, TravelTip
from backend.app.travel.models.geo import City, Country, State


class DestinationRepository:
    """Repository for Destination entities and related classifications."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, destination_id: UUID) -> Optional[Destination]:
        stmt = (
            select(Destination)
            .options(
                selectinload(Destination.seasons),
                selectinload(Destination.travel_tips),
                selectinload(Destination.attractions),
                selectinload(Destination.activities),
                selectinload(Destination.hotels),
                selectinload(Destination.restaurants),
                selectinload(Destination.transportation_options),
                selectinload(Destination.travel_routes),
                selectinload(Destination.trust_metric),
                selectinload(Destination.tags),
                selectinload(Destination.city),
                selectinload(Destination.state_rel),
                selectinload(Destination.country),
                selectinload(Destination.category_entity),
            )
            .where(Destination.id == destination_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_slug(self, slug: str) -> Optional[Destination]:
        stmt = (
            select(Destination)
            .options(
                selectinload(Destination.seasons),
                selectinload(Destination.travel_tips),
                selectinload(Destination.attractions),
                selectinload(Destination.activities),
                selectinload(Destination.hotels),
                selectinload(Destination.restaurants),
                selectinload(Destination.transportation_options),
                selectinload(Destination.travel_routes),
                selectinload(Destination.trust_metric),
                selectinload(Destination.tags),
                selectinload(Destination.city),
                selectinload(Destination.state_rel),
                selectinload(Destination.country),
                selectinload(Destination.category_entity),
            )
            .where(Destination.slug == slug)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_destinations(
        self,
        category: Optional[str] = None,
        region: Optional[str] = None,
        state: Optional[str] = None,
        budget: Optional[str] = None,
        is_hidden_gem: Optional[bool] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Destination]:
        stmt = select(Destination)

        if category:
            stmt = stmt.where(Destination.category.ilike(f"%{category}%"))
        if region:
            stmt = stmt.where(Destination.region == region)
        if state:
            stmt = stmt.where(Destination.state == state)
        if budget:
            stmt = stmt.where(Destination.budget == budget)
        if is_hidden_gem is not None:
            stmt = stmt.where(Destination.is_hidden_gem == is_hidden_gem)
        if search_query:
            term = f"%{search_query.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Destination.name).like(term),
                    func.lower(Destination.description).like(term),
                    func.lower(Destination.state).like(term),
                )
            )

        stmt = stmt.order_by(Destination.trust_score.desc(), Destination.name).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_nearby(
        self,
        latitude: float,
        longitude: float,
        max_distance_deg: float = 1.0,
        limit: int = 10,
    ) -> Sequence[Destination]:
        """Simple bounding box lookup based on coordinates."""
        stmt = (
            select(Destination)
            .where(
                Destination.latitude.isnot(None),
                Destination.longitude.isnot(None),
                Destination.latitude >= latitude - max_distance_deg,
                Destination.latitude <= latitude + max_distance_deg,
                Destination.longitude >= longitude - max_distance_deg,
                Destination.longitude <= longitude + max_distance_deg,
            )
            .order_by(Destination.trust_score.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_destination(self, **kwargs) -> Destination:
        destination = Destination(**kwargs)
        self.session.add(destination)
        await self.session.flush()
        return destination

    # Categories
    async def get_or_create_category(self, slug: str, name: str, **kwargs) -> DestinationCategory:
        stmt = select(DestinationCategory).where(DestinationCategory.slug == slug)
        result = await self.session.execute(stmt)
        cat = result.scalars().first()
        if not cat:
            cat = DestinationCategory(slug=slug, name=name, **kwargs)
            self.session.add(cat)
            await self.session.flush()
        return cat

    async def list_categories(self) -> Sequence[DestinationCategory]:
        stmt = select(DestinationCategory).order_by(DestinationCategory.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # Seasons & Tips
    async def add_season(self, destination_id: UUID, **kwargs) -> Season:
        season = Season(destination_id=destination_id, **kwargs)
        self.session.add(season)
        await self.session.flush()
        return season

    async def add_travel_tip(self, destination_id: UUID, **kwargs) -> TravelTip:
        tip = TravelTip(destination_id=destination_id, **kwargs)
        self.session.add(tip)
        await self.session.flush()
        return tip
