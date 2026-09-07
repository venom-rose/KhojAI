"""Nominatim OpenStreetMap Geocoding and Place Provider with strict rate limiting."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config.settings import settings
from backend.app.travel.providers.base import TravelDataProvider
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)

logger = logging.getLogger("khojai.travel.providers.nominatim")


class NominatimProvider(TravelDataProvider):
    """Nominatim OSM Geocoding & Place discovery adapter adhering to OSM usage policies."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(provider_name="nominatim")
        self.base_url = (base_url or getattr(settings, "NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")).rstrip("/")
        self.user_agent = user_agent or getattr(settings, "NOMINATIM_USER_AGENT", "KHOJAI-Travel-App/1.0 (contact@khojai.com)")
        self.timeout = timeout or settings.TRAVEL_API_TIMEOUT_SECONDS
        self._last_request_time: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(self.user_agent and len(self.user_agent.strip()) > 5)

    async def _rate_limited_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Enforces OSM usage policy: at least 1.0 second between consecutive requests."""
        if not self.is_configured:
            return None

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        url = f"{self.base_url}{endpoint}"

        async with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < 1.05:
                await asyncio.sleep(1.05 - elapsed)
            self._last_request_time = time.time()

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    if resp.status_code == 429:
                        logger.warning("Nominatim rate limit exceeded (429). Backing off for 2.5s...")
                        await asyncio.sleep(2.5)
                        return None
                    resp.raise_for_status()
                    return resp.json()
            except Exception as e:
                logger.error(f"Nominatim request error: {e}")
                return None

    async def search_places(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 10000,
        included_types: Optional[List[str]] = None,
        limit: int = 10,
        **kwargs,
    ) -> List[TravelPlace]:
        """Search places/geolocations by query string."""
        if not self.is_configured or not query:
            return []

        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": limit,
            "countrycodes": "in",
        }

        data = await self._rate_limited_get("/search", params=params)
        if not data or not isinstance(data, list):
            return []

        places = []
        for item in data:
            name = item.get("name") or item.get("display_name", "").split(",")[0]
            lat = float(item["lat"]) if "lat" in item else None
            lon = float(item["lon"]) if "lon" in item else None
            places.append(
                TravelPlace(
                    name=name,
                    place_id=str(item.get("place_id", "")),
                    formatted_address=item.get("display_name"),
                    latitude=lat,
                    longitude=lon,
                    types=[item.get("category"), item.get("type")] if item.get("category") else [],
                    provider="nominatim",
                    provider_id=str(item.get("place_id", "")),
                    metadata={"osm_type": item.get("osm_type"), "osm_id": item.get("osm_id")},
                )
            )
        return places

    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[TravelPlace]:
        """Reverse geocode coordinates to an address/place."""
        if not self.is_configured:
            return None

        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "jsonv2",
            "addressdetails": 1,
        }
        item = await self._rate_limited_get("/reverse", params=params)
        if not item or not isinstance(item, dict):
            return None

        name = item.get("name") or item.get("display_name", "").split(",")[0]
        return TravelPlace(
            name=name,
            place_id=str(item.get("place_id", "")),
            formatted_address=item.get("display_name"),
            latitude=latitude,
            longitude=longitude,
            types=[item.get("category"), item.get("type")] if item.get("category") else [],
            provider="nominatim",
            provider_id=str(item.get("place_id", "")),
        )

    async def get_place_details(self, place_id: str, **kwargs) -> Optional[TravelPlace]:
        """Fetch details by place_id."""
        if not self.is_configured or not place_id:
            return None

        params = {
            "place_id": place_id,
            "format": "json",
            "addressdetails": 1,
        }
        item = await self._rate_limited_get("/details", params=params)
        if not item or not isinstance(item, dict):
            return None

        coords = item.get("geometry", {}).get("coordinates", [None, None])
        return TravelPlace(
            name=item.get("localname") or item.get("names", {}).get("name", "Place"),
            place_id=place_id,
            formatted_address=item.get("calculated_postcode") or item.get("country_code"),
            latitude=coords[1] if len(coords) > 1 else None,
            longitude=coords[0] if len(coords) > 0 else None,
            types=[item.get("category", "place")],
            provider="nominatim",
            provider_id=place_id,
        )

    async def autocomplete_places(
        self,
        input_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 50000,
        **kwargs,
    ) -> List[TravelPlaceAutocompleteItem]:
        # Nominatim policy forbids high-frequency keystroke autocomplete queries.
        return []

    async def search_hotels(self, **kwargs) -> List[TravelHotel]:
        return []

    async def search_flights(self, **kwargs) -> List[TravelFlight]:
        return []

    async def search_activities(self, **kwargs) -> List[TravelActivity]:
        return []

    async def search_airports(self, **kwargs) -> List[TravelAirport]:
        return []
