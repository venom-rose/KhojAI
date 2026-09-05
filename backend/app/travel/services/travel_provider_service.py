"""Resilient Travel Provider Service coordinating AirLabs, OpenTripMap, Google Places, and Local DB."""

import logging
from typing import Any, Dict, List, Optional

from backend.app.config.settings import settings
from backend.app.travel.cache.cache_manager import travel_cache
from backend.app.travel.providers.airlabs_provider import AirLabsProvider
from backend.app.travel.providers.opentripmap_provider import OpenTripMapProvider
from backend.app.travel.providers.google_places_provider import GooglePlacesProvider
from backend.app.travel.providers.local_db_provider import LocalDatabaseProvider
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)

logger = logging.getLogger("khojai.travel.services.provider_service")


class TravelProviderService:
    """High-level service managing provider routing, caching, rate-limit fallback, and resilience.

    Provider routing:
    - Hotels:     Google Places → Local DB
    - Flights:    AirLabs (routes/schedules) → empty (no real-time pricing)
    - Activities: OpenTripMap → Local DB
    - Airports:   AirLabs → Local DB
    - Places:     Google Places → OpenTripMap → Local DB
    - Autocomplete: Google Places → OpenTripMap → Local DB
    """

    def __init__(
        self,
        airlabs_provider: Optional[AirLabsProvider] = None,
        opentripmap_provider: Optional[OpenTripMapProvider] = None,
        google_provider: Optional[GooglePlacesProvider] = None,
        local_db_provider: Optional[LocalDatabaseProvider] = None,
    ):
        self.airlabs = airlabs_provider or AirLabsProvider()
        self.opentripmap = opentripmap_provider or OpenTripMapProvider()
        self.google = google_provider or GooglePlacesProvider()
        self.local_db = local_db_provider or LocalDatabaseProvider()

    # --- Hotels (Google Places primary, Local DB fallback) ---
    async def get_hotels(
        self,
        city_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: int = 20,
        limit: int = 15,
        force_refresh: bool = False,
    ) -> List[TravelHotel]:
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

        # Google Places: search for hotel type near location
        if self.google.is_configured and (latitude is not None or city_code):
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
                # Convert TravelPlace → TravelHotel
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
            except Exception as exc:
                logger.warning(f"Google Places hotel search failed ({exc}). Falling back to Local DB.")

        # Fallback to Local DB
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

    # --- Flights (AirLabs — schedule/route data, not live prices) ---
    async def get_flights(
        self,
        origin_code: str,
        destination_code: str,
        departure_date: str,
        adults: int = 1,
        return_date: Optional[str] = None,
        limit: int = 10,
        force_refresh: bool = False,
    ) -> List[TravelFlight]:
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
        if self.airlabs.is_configured:
            try:
                flights = await self.airlabs.search_flights(
                    origin_code=origin_code,
                    destination_code=destination_code,
                    departure_date=departure_date,
                    adults=adults,
                    return_date=return_date,
                    limit=limit,
                )
            except Exception as exc:
                logger.warning(f"AirLabs flight/route search failed ({exc}).")

        if flights:
            await travel_cache.set(cache_key, [f.model_dump() for f in flights])
        return flights

    # --- Activities (OpenTripMap primary, Local DB fallback) ---
    async def get_activities(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 25,
        limit: int = 15,
        force_refresh: bool = False,
    ) -> List[TravelActivity]:
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
        if self.opentripmap.is_configured:
            try:
                activities = await self.opentripmap.search_activities(
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                    limit=limit,
                )
            except Exception as exc:
                logger.warning(f"OpenTripMap activity search failed ({exc}). Falling back to Local DB.")

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

    # --- Airports (AirLabs primary, Local DB fallback) ---
    async def get_airports(
        self,
        keyword: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit: int = 10,
        force_refresh: bool = False,
    ) -> List[TravelAirport]:
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
        if self.airlabs.is_configured:
            try:
                airports = await self.airlabs.search_airports(
                    keyword=keyword,
                    latitude=latitude,
                    longitude=longitude,
                    limit=limit,
                )
            except Exception as exc:
                logger.warning(f"AirLabs airport search failed ({exc}). Falling back to Local DB.")

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

    # --- Places (Google Places Primary) ---
    async def get_places(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 10000,
        included_types: Optional[List[str]] = None,
        limit: int = 15,
        force_refresh: bool = False,
    ) -> List[TravelPlace]:
        cache_key = travel_cache.make_key(
            "places",
            q=query,
            lat=latitude,
            lon=longitude,
            rad=radius_meters,
            types=included_types,
            lim=limit,
        )
        if not force_refresh:
            cached = await travel_cache.get(cache_key)
            if cached is not None:
                return [TravelPlace(**p) if isinstance(p, dict) else p for p in cached]

        places: List[TravelPlace] = []
        if self.google.is_configured:
            try:
                places = await self.google.search_places(
                    query=query,
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=radius_meters,
                    included_types=included_types,
                    limit=limit,
                )
            except Exception as exc:
                logger.warning(f"Google Places search failed ({exc}). Falling back to Local DB.")

        if not places:
            logger.info("Serving places from Local Database fallback.")
            places = await self.local_db.search_places(
                query=query,
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters,
                included_types=included_types,
                limit=limit,
            )

        if places:
            await travel_cache.set(cache_key, [p.model_dump() for p in places])
        return places

    async def get_place_details(
        self,
        place_id: str,
        force_refresh: bool = False,
    ) -> Optional[TravelPlace]:
        cache_key = travel_cache.make_key("place_details", pid=place_id)
        if not force_refresh:
            cached = await travel_cache.get(cache_key)
            if cached is not None:
                return TravelPlace(**cached) if isinstance(cached, dict) else cached

        place = None
        if self.google.is_configured:
            try:
                place = await self.google.get_place_details(place_id)
            except Exception as exc:
                logger.warning(f"Google Place details failed for {place_id} ({exc}).")

        if not place:
            place = await self.local_db.get_place_details(place_id)

        if place:
            await travel_cache.set(cache_key, place.model_dump())
        return place

    async def autocomplete_places(
        self,
        input_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 50000,
    ) -> List[TravelPlaceAutocompleteItem]:
        cache_key = travel_cache.make_key(
            "autocomplete",
            inp=input_text,
            lat=latitude,
            lon=longitude,
            rad=radius_meters,
        )
        cached = await travel_cache.get(cache_key)
        if cached is not None:
            return [TravelPlaceAutocompleteItem(**item) if isinstance(item, dict) else item for item in cached]

        items: List[TravelPlaceAutocompleteItem] = []
        if self.google.is_configured:
            try:
                items = await self.google.autocomplete_places(
                    input_text=input_text,
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=radius_meters,
                )
            except Exception as exc:
                logger.warning(f"Google Places autocomplete failed ({exc}). Falling back to Local DB.")

        if not items:
            items = await self.local_db.autocomplete_places(
                input_text=input_text,
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters,
            )

        if items:
            await travel_cache.set(cache_key, [item.model_dump() for item in items], ttl_seconds=86400)
        return items

    async def fetch_place_photo(self, photo_name: str) -> Optional[tuple[bytes, str]]:
        """Proxy Google Places photo bytes without exposing the API key to client."""
        return await self.google.fetch_photo_bytes(photo_name)
