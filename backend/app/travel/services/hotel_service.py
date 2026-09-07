"""Hotel Service coordinating Amadeus, Google Places, Geoapify, and Local DB."""

import logging
from typing import Any, Dict, List, Optional

from backend.app.travel.cache.cache_manager import travel_cache
from backend.app.travel.providers.amadeus_provider import AmadeusProvider
from backend.app.travel.providers.google_places_provider import GooglePlacesProvider
from backend.app.travel.providers.geoapify_provider import GeoapifyProvider
from backend.app.travel.providers.local_db_provider import LocalDatabaseProvider
from backend.app.travel.schemas.internal import TravelHotel

logger = logging.getLogger("khojai.travel.services.hotel")


class HotelService:
    """Service handling multi-provider hotel searches with caching and fallback."""

    def __init__(
        self,
        amadeus_provider: Optional[AmadeusProvider] = None,
        google_provider: Optional[GooglePlacesProvider] = None,
        geoapify_provider: Optional[GeoapifyProvider] = None,
        local_db_provider: Optional[LocalDatabaseProvider] = None,
    ):
        self.amadeus = amadeus_provider or AmadeusProvider()
        self.google = google_provider or GooglePlacesProvider()
        self.geoapify = geoapify_provider or GeoapifyProvider()
        self.local_db = local_db_provider or LocalDatabaseProvider()

    async def search_hotels(
        self,
        city_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: int = 20,
        limit: int = 15,
        force_refresh: bool = False,
    ) -> List[TravelHotel]:
        """Search hotels across Amadeus -> Google Places -> Geoapify -> Local DB."""
        cache_key = travel_cache.make_key(
            "hotels",
            city_code=city_code,
            lat=latitude,
            lon=longitude,
            rad=radius_km,
            lim=limit,
        )
        if not force_refresh:
            cached = await travel_cache.get(cache_key)
            if cached is not None:
                return [TravelHotel(**h) if isinstance(h, dict) else h for h in cached]

        hotels: List[TravelHotel] = []

        # 1. Try Amadeus if configured
        if self.amadeus.is_configured and (city_code or (latitude is not None and longitude is not None)):
            try:
                hotels = await self.amadeus.search_hotels(
                    city_code=city_code,
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"Amadeus hotel search failed: {e}. Trying Google Places.")

        # 2. Try Google Places if still empty
        if not hotels and self.google.is_configured and (latitude is not None or city_code):
            try:
                query = f"hotels in {city_code}" if city_code else "hotels"
                places = await self.google.search_places(
                    query=query,
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=radius_km * 1000,
                    included_types=["lodging"],
                    limit=limit,
                )
                for p in places:
                    hotels.append(
                        TravelHotel(
                            name=p.name,
                            hotel_id=p.place_id,
                            latitude=p.latitude,
                            longitude=p.longitude,
                            address=p.formatted_address,
                            rating=p.rating,
                            price_tier=p.price_level,
                            amenities=[],
                            photo_urls=[ph.proxy_url or ph.photo_reference for ph in p.photos if ph],
                            provider="google_places",
                            provider_id=p.place_id,
                        )
                    )
            except Exception as e:
                logger.warning(f"Google Places hotel search failed: {e}. Trying Geoapify.")

        # 3. Try Geoapify if still empty
        if not hotels and self.geoapify.is_configured and (latitude is not None or city_code):
            try:
                hotels = await self.geoapify.search_hotels(
                    city_code=city_code,
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"Geoapify hotel search failed: {e}. Falling back to Local DB.")

        # 4. Fallback to Local DB
        if not hotels:
            logger.info("Serving hotels from Local Database fallback.")
            hotels = await self.local_db.search_hotels(
                city_code=city_code,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                limit=limit,
            )

        if hotels:
            await travel_cache.set(cache_key, [h.model_dump() for h in hotels])
        return hotels
