"""Destination Service managing destinations, regional guides, and curated experiences."""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database.session import AsyncSessionFactory
from backend.app.models.destination import Destination
from backend.app.travel.cache.cache_manager import travel_cache
from backend.app.travel.normalizers.destination_normalizer import DestinationNormalizer
from backend.app.travel.schemas.internal import TravelActivity, TravelDestination

logger = logging.getLogger("khojai.travel.services.destination")


class DestinationService:
    """Service handling destination search, slug resolution, and experiences."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or AsyncSessionFactory

    async def search_destinations(
        self,
        query: Optional[str] = None,
        state: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
        force_refresh: bool = False,
        db: Optional[AsyncSession] = None,
    ) -> List[TravelDestination]:
        """Search destinations by text query, state, or category."""
        cache_key = travel_cache.make_key("dest_search", q=query, s=state, cat=category, lim=limit)
        if not force_refresh:
            cached = await travel_cache.get(cache_key)
            if cached is not None:
                return [TravelDestination(**d) if isinstance(d, dict) else d for d in cached]

        async def _query(session: AsyncSession):
            stmt = select(Destination).limit(limit)
            if query:
                q_pattern = f"%{query.strip().lower()}%"
                stmt = stmt.where(
                    or_(
                        func.lower(Destination.name).like(q_pattern),
                        func.lower(Destination.state).like(q_pattern),
                        func.lower(Destination.category).like(q_pattern),
                        func.lower(Destination.description).like(q_pattern),
                    )
                )
            if state:
                stmt = stmt.where(func.lower(Destination.state) == state.strip().lower())
            if category:
                stmt = stmt.where(func.lower(Destination.category) == category.strip().lower())

            result = await session.execute(stmt)
            destinations = result.scalars().all()
            return [DestinationNormalizer.from_db_model(d) for d in destinations]

        if db is not None:
            normalized = await _query(db)
        else:
            async with self.session_factory() as session:
                normalized = await _query(session)

        if normalized:
            await travel_cache.set(cache_key, [d.model_dump() for d in normalized], ttl_seconds=86400)
        return normalized

    async def get_destination_by_slug(
        self,
        slug: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[TravelDestination]:
        """Retrieve destination details by slug."""
        cache_key = travel_cache.make_key("dest_slug", slug=slug)
        cached = await travel_cache.get(cache_key)
        if cached is not None:
            return TravelDestination(**cached) if isinstance(cached, dict) else cached

        async def _query(session: AsyncSession):
            stmt = select(Destination).where(Destination.slug == slug.lower().strip())
            result = await session.execute(stmt)
            dest = result.scalars().first()
            return DestinationNormalizer.from_db_model(dest) if dest else None

        if db is not None:
            normalized = await _query(db)
        else:
            async with self.session_factory() as session:
                normalized = await _query(session)

        if normalized:
            await travel_cache.set(cache_key, normalized.model_dump(), ttl_seconds=86400)
        return normalized

    async def get_destination_experiences(
        self,
        slug: str,
        limit: int = 15,
        db: Optional[AsyncSession] = None,
    ) -> List[TravelActivity]:
        """Retrieve curated experiences and activities for a destination."""
        dest = await self.get_destination_by_slug(slug, db=db)
        if not dest or dest.latitude is None or dest.longitude is None:
            return []

        from backend.app.travel.services.activity_service import ActivityService
        activity_svc = ActivityService(session_factory=self.session_factory)
        return await activity_svc.search_activities(
            latitude=dest.latitude,
            longitude=dest.longitude,
            radius_km=30,
            limit=limit,
        )
