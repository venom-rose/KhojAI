"""OpenTripMap Travel Data Provider — attractions, POIs, and activities.

OpenTripMap API (https://opentripmap.io) provides a comprehensive global
database of tourist attractions, cultural sites, natural landmarks, and
points of interest. Excellent coverage of India's lesser-known destinations.

Free tier: unlimited requests with rate limiting (~5 req/sec).
API key: sign up at https://opentripmap.io/register → API Key
Set environment variable: OPENTRIPMAP_API_KEY=your_key_here

API docs: https://opentripmap.io/docs
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config.settings import settings
from backend.app.travel.normalizers.opentripmap_normalizer import OpenTripMapNormalizer
from backend.app.travel.providers.base import TravelDataProvider
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)

logger = logging.getLogger("khojai.travel.providers.opentripmap")

OPENTRIPMAP_BASE_URL = "https://api.opentripmap.com/0.1/en/places"

# OpenTripMap interest categories relevant to KHOJAI's Indian travel focus
KHOJAI_INTERESTING_KINDS = (
    "historic,cultural,natural,religion,architecture,museums,theatres_and_entertainments,"
    "amusements,sport,industrial_facilities,other_hotels,foods,national_parks,"
    "water,beaches_and_water_sports,fishing,mountains,tourist_object"
)


class OpenTripMapProvider(TravelDataProvider):
    """OpenTripMap POI & attraction provider.

    Covers what Amadeus 'activities' endpoint previously provided, and more:
    - Attractions and cultural sites search by coordinates
    - POI detail retrieval
    - Place text search

    For airports and flight routes — AirLabsProvider is used instead.
    For hotels — Google Places or LocalDatabaseProvider is used instead.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        super().__init__(provider_name="opentripmap")
        self.api_key = api_key or getattr(settings, "OPENTRIPMAP_API_KEY", "")
        self.timeout = timeout or settings.TRAVEL_API_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.TRAVEL_API_MAX_RETRIES

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GET request against the OpenTripMap REST API."""
        if params is None:
            params = {}
        params["apikey"] = self.api_key
        url = f"{OPENTRIPMAP_BASE_URL}/{path}"

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(url, params=params)

                    if resp.status_code == 429:
                        import asyncio
                        wait = 2.0 * (2 ** attempt)
                        logger.warning(f"OpenTripMap rate limit (429). Backing off {wait}s...")
                        await asyncio.sleep(wait)
                        continue

                    resp.raise_for_status()
                    return resp.json()

            except (httpx.TimeoutException, httpx.NetworkError) as err:
                if attempt >= self.max_retries:
                    logger.error(f"OpenTripMap request failed after {self.max_retries} retries: {err}")
                    raise
                import asyncio
                await asyncio.sleep(1.0 * (2 ** attempt))

        raise RuntimeError(f"OpenTripMap request to /{path} failed after {self.max_retries} attempts.")

    # -------------------------------------------------------------------------
    # Activities — primary capability (replaces Amadeus /v1/shopping/activities)
    # -------------------------------------------------------------------------
    async def search_activities(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 25,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelActivity]:
        """Search tourist attractions and activities near a geographic point."""
        if not self.is_configured:
            logger.warning("OpenTripMap API key not configured. Skipping activity search.")
            return []

        try:
            radius_m = min(radius_km * 1000, 50000)  # API cap: 50km
            params = {
                "lat": round(latitude, 5),
                "lon": round(longitude, 5),
                "radius": radius_m,
                "kinds": KHOJAI_INTERESTING_KINDS,
                "rate": "2",          # Minimum WikiData rating (filters junk)
                "format": "json",
                "limit": min(limit * 2, 100),  # Fetch extra, filter after normalizing
            }
            data = await self._get("radius", params=params)
            activities = OpenTripMapNormalizer.normalize_activities(data)
            return activities[:limit]

        except Exception as exc:
            logger.error(f"OpenTripMap activity search error: {exc}")
            return []

    # -------------------------------------------------------------------------
    # Places search — text query
    # -------------------------------------------------------------------------
    async def search_places(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 10000,
        included_types: Optional[List[str]] = None,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelPlace]:
        """Search places by name query, optionally biased by coordinates."""
        if not self.is_configured:
            logger.warning("OpenTripMap API key not configured. Skipping place search.")
            return []

        try:
            params: Dict[str, Any] = {
                "name": query.strip(),
                "kinds": KHOJAI_INTERESTING_KINDS,
                "format": "json",
                "limit": min(limit, 100),
            }
            if latitude is not None and longitude is not None:
                params["lat"] = round(latitude, 5)
                params["lon"] = round(longitude, 5)
                params["radius"] = min(radius_meters, 50000)

            data = await self._get("radius" if latitude else "autosuggest", params=params)
            places = OpenTripMapNormalizer.normalize_places(data)
            return places[:limit]

        except Exception as exc:
            logger.error(f"OpenTripMap place search error: {exc}")
            return []

    # -------------------------------------------------------------------------
    # Place details — by OpenTripMap XID
    # -------------------------------------------------------------------------
    async def get_place_details(self, place_id: str, **kwargs) -> Optional[TravelPlace]:
        """Retrieve detailed information for an OpenTripMap XID."""
        if not self.is_configured:
            return None

        try:
            data = await self._get(f"xid/{place_id}")
            return OpenTripMapNormalizer.normalize_place_detail(data)
        except Exception as exc:
            logger.error(f"OpenTripMap place detail error for {place_id}: {exc}")
            return None

    # -------------------------------------------------------------------------
    # Autocomplete — uses OpenTripMap autosuggest
    # -------------------------------------------------------------------------
    async def autocomplete_places(
        self,
        input_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 50000,
        **kwargs,
    ) -> List[TravelPlaceAutocompleteItem]:
        """Predictive place name suggestions for search-as-you-type."""
        if not self.is_configured:
            return []

        try:
            params: Dict[str, Any] = {
                "name": input_text.strip(),
                "kinds": KHOJAI_INTERESTING_KINDS,
                "format": "json",
                "limit": 10,
            }
            if latitude is not None and longitude is not None:
                params["lat"] = round(latitude, 5)
                params["lon"] = round(longitude, 5)
                params["radius"] = min(radius_meters, 50000)

            data = await self._get("autosuggest", params=params)
            return OpenTripMapNormalizer.normalize_autocomplete(data)

        except Exception as exc:
            logger.error(f"OpenTripMap autocomplete error: {exc}")
            return []

    # -------------------------------------------------------------------------
    # Unsupported — delegated to other providers
    # -------------------------------------------------------------------------
    async def search_hotels(self, **kwargs) -> List[TravelHotel]:
        """OpenTripMap does not provide hotel booking data."""
        return []

    async def search_flights(self, **kwargs) -> List[TravelFlight]:
        """OpenTripMap does not provide flight data. Use AirLabsProvider."""
        return []

    async def search_airports(self, **kwargs) -> List[TravelAirport]:
        """OpenTripMap does not provide airport data. Use AirLabsProvider."""
        return []
