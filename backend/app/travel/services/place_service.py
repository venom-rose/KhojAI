"""Place Service coordinating Google Places, Geoapify, OpenTripMap, Nominatim, and Local DB."""

import logging
from typing import Any, Dict, List, Optional

from backend.app.travel.cache.cache_manager import travel_cache
from backend.app.travel.providers.google_places_provider import GooglePlacesProvider
from backend.app.travel.providers.geoapify_provider import GeoapifyProvider
from backend.app.travel.providers.opentripmap_provider import OpenTripMapProvider
from backend.app.travel.providers.nominatim_provider import NominatimProvider
from backend.app.travel.providers.local_db_provider import LocalDatabaseProvider
from backend.app.travel.schemas.internal import TravelPlace, TravelPlaceAutocompleteItem

logger = logging.getLogger("khojai.travel.services.place")


class PlaceService:
    """Service handling place discovery, autocomplete, details, and photos with fallback."""

    def __init__(
        self,
        google_provider: Optional[GooglePlacesProvider] = None,
        geoapify_provider: Optional[GeoapifyProvider] = None,
        opentripmap_provider: Optional[OpenTripMapProvider] = None,
        nominatim_provider: Optional[NominatimProvider] = None,
        local_db_provider: Optional[LocalDatabaseProvider] = None,
    ):
        self.google = google_provider or GooglePlacesProvider()
        self.geoapify = geoapify_provider or GeoapifyProvider()
        self.opentripmap = opentripmap_provider or OpenTripMapProvider()
        self.nominatim = nominatim_provider or NominatimProvider()
        self.local_db = local_db_provider or LocalDatabaseProvider()

    async def search_places(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 10000,
        included_types: Optional[List[str]] = None,
        limit: int = 15,
        force_refresh: bool = False,
    ) -> List[TravelPlace]:
        """Search places across Google Places -> Geoapify -> OpenTripMap -> Nominatim -> Local DB."""
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

        # 1. Try Google Places
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
            except Exception as e:
                logger.warning(f"Google Places search failed: {e}. Trying Geoapify.")

        # 2. Try Geoapify
        if not places and self.geoapify.is_configured:
            try:
                places = await self.geoapify.search_places(
                    query=query,
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=radius_meters,
                    included_types=included_types,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"Geoapify search failed: {e}. Trying Nominatim/Local DB.")

        # 3. Try Nominatim if text query exists
        if not places and self.nominatim.is_configured and query:
            try:
                places = await self.nominatim.search_places(
                    query=query,
                    limit=limit,
                )
            except Exception as e:
                logger.warning(f"Nominatim search failed: {e}. Falling back to Local DB.")

        # 4. Fallback to Local DB
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

    async def get_place_details(self, place_id: str, force_refresh: bool = False) -> Optional[TravelPlace]:
        """Retrieve place details from Google Places -> Geoapify -> Nominatim -> Local DB."""
        cache_key = travel_cache.make_key("place_details", pid=place_id)
        if not force_refresh:
            cached = await travel_cache.get(cache_key)
            if cached is not None:
                return TravelPlace(**cached) if isinstance(cached, dict) else cached

        place = None

        # 1. Google Places
        if self.google.is_configured:
            try:
                place = await self.google.get_place_details(place_id)
            except Exception as e:
                logger.warning(f"Google Place details failed: {e}. Trying Geoapify.")

        # 2. Geoapify
        if not place and self.geoapify.is_configured:
            try:
                place = await self.geoapify.get_place_details(place_id)
            except Exception as e:
                logger.warning(f"Geoapify place details failed: {e}.")

        # 3. Local DB
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
        """Autocomplete places across Google Places -> Geoapify -> Local DB."""
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
            except Exception as e:
                logger.warning(f"Google Places autocomplete failed: {e}. Trying Geoapify.")

        if not items and self.geoapify.is_configured:
            try:
                items = await self.geoapify.autocomplete_places(
                    input_text=input_text,
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=radius_meters,
                )
            except Exception as e:
                logger.warning(f"Geoapify autocomplete failed: {e}. Falling back to Local DB.")

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
        """Proxy Google Places photo bytes securely without exposing API key."""
        return await self.google.fetch_photo_bytes(photo_name)

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[TravelPlace]:
        """Reverse geocode coordinates using Nominatim."""
        return await self.nominatim.reverse_geocode(latitude, longitude)
