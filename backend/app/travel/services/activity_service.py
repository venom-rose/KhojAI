"""Activity Service coordinating Amadeus, OpenTripMap, Geoapify, and Local DB activities."""

import logging
from typing import Any, Dict, List, Optional

from backend.app.travel.cache.cache_manager import travel_cache
from backend.app.travel.providers.amadeus_provider import AmadeusProvider
from backend.app.travel.providers.opentripmap_provider import OpenTripMapProvider
from backend.app.travel.providers.geoapify_provider import GeoapifyProvider
from backend.app.travel.providers.local_db_provider import LocalDatabaseProvider
from backend.app.travel.schemas.internal import TravelActivity

logger = logging.getLogger("khojai.travel.services.activity")


class ActivityService:
    """Service handling multi-provider activities and tour searches with caching."""

    def __init__(
        self,
        amadeus_provider: Optional[AmadeusProvider] = None,
        opentripmap_provider: Optional[OpenTripMapProvider] = None,
        geoapify_provider: Optional[GeoapifyProvider] = None,
        local_db_provider: Optional[LocalDatabaseProvider] = None,
        session_factory=None,
    ):
        self.amadeus = amadeus_provider or AmadeusProvider()
        self.opentripmap = opentripmap_provider or OpenTripMapProvider()
        self.geoapify = geoapify_provider or GeoapifyProvider()
        self.local_db = local_db_provider or LocalDatabaseProvider(session_factory=session_factory)

    async def search_activities(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 25,
        limit: int = 15,
        force_refresh: bool = False,
    ) -> List[TravelActivity]:
        """Search activities across Amadeus -> OpenTripMap -> Geoapify -> Local DB."""
        cache_key = travel_cache.make_key(
            "activities",
            lat=latitude,
            lon=longitude,
            rad=radius_km,
            lim=limit,
        )
        if not force_refresh:
            cached = await travel_cache.get(cache_key)
            if cached is not None:
                return [TravelActivity(**a) if isinstance(a, dict) else a for a in cached]

        activities: List[TravelActivity] = []

        # 1. Try Amadeus
        if self.amadeus.is_configured:
            try:
                activities = await self.amadeus.search_activities(
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"Amadeus activities search failed: {e}. Trying OpenTripMap.")

        # 2. Try OpenTripMap
        if not activities and self.opentripmap.is_configured:
            try:
                activities = await self.opentripmap.search_activities(
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"OpenTripMap activities search failed: {e}. Trying Geoapify.")

        # 3. Try Geoapify
        if not activities and self.geoapify.is_configured:
            try:
                activities = await self.geoapify.search_activities(
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"Geoapify activities search failed: {e}. Falling back to Local DB.")

        # 4. Fallback to Local DB
        if not activities:
            logger.info("Serving activities from Local Database fallback.")
            activities = await self.local_db.search_activities(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                limit=limit,
            )

        if activities:
            await travel_cache.set(cache_key, [a.model_dump() for a in activities])
        return activities
