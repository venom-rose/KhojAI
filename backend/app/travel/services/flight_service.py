"""Flight Service coordinating Amadeus, AirLabs, and Local DB transit routes."""

import logging
from typing import Any, Dict, List, Optional

from backend.app.travel.cache.cache_manager import travel_cache
from backend.app.travel.providers.amadeus_provider import AmadeusProvider
from backend.app.travel.providers.airlabs_provider import AirLabsProvider
from backend.app.travel.providers.local_db_provider import LocalDatabaseProvider
from backend.app.travel.schemas.internal import TravelAirport, TravelFlight

logger = logging.getLogger("khojai.travel.services.flight")


class FlightService:
    """Service handling flight search and airport lookup with provider failover."""

    def __init__(
        self,
        amadeus_provider: Optional[AmadeusProvider] = None,
        airlabs_provider: Optional[AirLabsProvider] = None,
        local_db_provider: Optional[LocalDatabaseProvider] = None,
    ):
        self.amadeus = amadeus_provider or AmadeusProvider()
        self.airlabs = airlabs_provider or AirLabsProvider()
        self.local_db = local_db_provider or LocalDatabaseProvider()

    async def search_flights(
        self,
        origin_code: str,
        destination_code: str,
        departure_date: str,
        adults: int = 1,
        return_date: Optional[str] = None,
        limit: int = 10,
        force_refresh: bool = False,
    ) -> List[TravelFlight]:
        """Search flight offers across Amadeus -> AirLabs."""
        cache_key = travel_cache.make_key(
            "flights",
            org=origin_code,
            dst=destination_code,
            dep=departure_date,
            ret=return_date,
            adl=adults,
            lim=limit,
        )
        if not force_refresh:
            cached = await travel_cache.get(cache_key)
            if cached is not None:
                return [TravelFlight(**f) if isinstance(f, dict) else f for f in cached]

        flights: List[TravelFlight] = []

        # 1. Try Amadeus
        if self.amadeus.is_configured:
            try:
                flights = await self.amadeus.search_flights(
                    origin_code=origin_code,
                    destination_code=destination_code,
                    departure_date=departure_date,
                    adults=adults,
                    return_date=return_date,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"Amadeus flight search failed: {e}. Trying AirLabs fallback.")

        # 2. Try AirLabs routes/schedules if empty
        if not flights and self.airlabs.is_configured:
            try:
                flights = await self.airlabs.search_flights(
                    origin_code=origin_code,
                    destination_code=destination_code,
                    departure_date=departure_date,
                    adults=adults,
                    return_date=return_date,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"AirLabs flight search failed: {e}.")

        if flights:
            await travel_cache.set(cache_key, [f.model_dump() for f in flights])
        return flights

    async def search_airports(
        self,
        keyword: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit: int = 10,
        force_refresh: bool = False,
    ) -> List[TravelAirport]:
        """Search airports across Amadeus -> AirLabs -> Local DB."""
        cache_key = travel_cache.make_key(
            "airports",
            kw=keyword,
            lat=latitude,
            lon=longitude,
            lim=limit,
        )
        if not force_refresh:
            cached = await travel_cache.get(cache_key)
            if cached is not None:
                return [TravelAirport(**a) if isinstance(a, dict) else a for a in cached]

        airports: List[TravelAirport] = []

        # 1. Try Amadeus
        if self.amadeus.is_configured:
            try:
                airports = await self.amadeus.search_airports(
                    keyword=keyword,
                    latitude=latitude,
                    longitude=longitude,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"Amadeus airport search failed: {e}. Trying AirLabs.")

        # 2. Try AirLabs
        if not airports and self.airlabs.is_configured:
            try:
                airports = await self.airlabs.search_airports(
                    keyword=keyword,
                    latitude=latitude,
                    longitude=longitude,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"AirLabs airport search failed: {e}. Falling back to Local DB.")

        # 3. Fallback to Local DB
        if not airports:
            airports = await self.local_db.search_airports(
                keyword=keyword,
                latitude=latitude,
                longitude=longitude,
                limit=limit,
            )

        if airports:
            await travel_cache.set(cache_key, [a.model_dump() for a in airports])
        return airports
