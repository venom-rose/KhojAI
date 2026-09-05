"""AirLabs Aviation Data Provider — airports, routes, and flight schedule data.

AirLabs API (https://airlabs.co) is a modern aviation data provider with a
generous free tier (1,000 req/month) covering airports, airlines, routes,
and real-time flight schedules.

API key: sign up at https://airlabs.co → Dashboard → API Key
Set environment variable: AIRLABS_API_KEY=your_key_here
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from backend.app.config.settings import settings
from backend.app.travel.normalizers.airlabs_normalizer import AirLabsNormalizer
from backend.app.travel.providers.base import TravelDataProvider
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)

logger = logging.getLogger("khojai.travel.providers.airlabs")

AIRLABS_BASE_URL = "https://airlabs.co/api/v9"


class AirLabsProvider(TravelDataProvider):
    """AirLabs aviation data adapter — airports, airlines, routes, and schedules.

    Handles the core aviation data that Amadeus Self-Service previously covered:
    - Airport search by keyword or coordinates
    - Flight route/schedule lookup between IATA codes

    For activities, hotels, and places — OpenTripMapProvider or Google Places
    are used instead (see TravelProviderService routing).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        super().__init__(provider_name="airlabs")
        self.api_key = api_key or getattr(settings, "AIRLABS_API_KEY", "")
        self.timeout = timeout or settings.TRAVEL_API_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.TRAVEL_API_MAX_RETRIES

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GET request against the AirLabs REST API with retry logic."""
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        url = f"{AIRLABS_BASE_URL}/{endpoint}"

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(url, params=params)

                    if resp.status_code == 429:
                        import asyncio
                        wait = 2.0 * (2 ** attempt)
                        logger.warning(f"AirLabs rate limit (429). Backing off {wait}s...")
                        await asyncio.sleep(wait)
                        continue

                    resp.raise_for_status()
                    return resp.json()

            except (httpx.TimeoutException, httpx.NetworkError) as err:
                if attempt >= self.max_retries:
                    logger.error(f"AirLabs request failed after {self.max_retries} retries: {err}")
                    raise
                import asyncio
                await asyncio.sleep(1.0 * (2 ** attempt))

        raise RuntimeError(f"AirLabs request to /{endpoint} failed after {self.max_retries} attempts.")

    # -------------------------------------------------------------------------
    # Airport search — primary capability
    # -------------------------------------------------------------------------
    async def search_airports(
        self,
        keyword: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit: int = 10,
        **kwargs,
    ) -> List[TravelAirport]:
        if not self.is_configured:
            logger.warning("AirLabs API key not configured. Skipping airport search.")
            return []

        try:
            params: Dict[str, Any] = {}
            if keyword:
                # Search by airport name, city name, or IATA code
                params["search"] = keyword.strip()
                data = await self._get("airports", params=params)
            elif latitude is not None and longitude is not None:
                # AirLabs supports lat/lng bounding queries via city search
                # Use a reasonable degree delta (~200km) to find nearby airports
                data = await self._get("airports", params=params)
                # Filter by proximity post-fetch since AirLabs doesn't support
                # geo-radius directly on free tier; normalizer handles sorting
                if "response" in data:
                    data["response"] = _filter_by_proximity(
                        data["response"], latitude, longitude, radius_km=250
                    )
            else:
                return []

            airports = AirLabsNormalizer.normalize_airports(data)
            return airports[:limit]

        except Exception as exc:
            logger.error(f"AirLabs airport search error: {exc}")
            return []

    # -------------------------------------------------------------------------
    # Flight routes — returns route schedules (not real-time booking offers)
    # -------------------------------------------------------------------------
    async def search_flights(
        self,
        origin_code: str,
        destination_code: str,
        departure_date: str,
        adults: int = 1,
        return_date: Optional[str] = None,
        limit: int = 10,
        **kwargs,
    ) -> List[TravelFlight]:
        """Search scheduled routes between two IATA airport codes.

        Note: AirLabs provides route/schedule data, not live booking prices.
        Use Duffel (duffel.com) if real-time pricing and booking is required.
        """
        if not self.is_configured:
            logger.warning("AirLabs API key not configured. Skipping flight route search.")
            return []

        try:
            params = {
                "dep_iata": origin_code.upper().strip(),
                "arr_iata": destination_code.upper().strip(),
            }
            data = await self._get("routes", params=params)
            flights = AirLabsNormalizer.normalize_routes(
                data,
                origin_code=origin_code.upper(),
                destination_code=destination_code.upper(),
                departure_date=departure_date,
            )
            return flights[:limit]

        except Exception as exc:
            logger.error(f"AirLabs route search error: {exc}")
            return []

    # -------------------------------------------------------------------------
    # Unsupported capabilities — delegated to OpenTripMap or Google Places
    # -------------------------------------------------------------------------
    async def search_hotels(self, **kwargs) -> List[TravelHotel]:
        """AirLabs does not provide hotel data. Delegated to Google Places / Local DB."""
        return []

    async def search_activities(self, **kwargs) -> List[TravelActivity]:
        """AirLabs does not provide activity data. Delegated to OpenTripMap / Local DB."""
        return []

    async def search_places(self, **kwargs) -> List[TravelPlace]:
        """AirLabs does not provide place search. Delegated to OpenTripMap / Google Places."""
        return []

    async def get_place_details(self, place_id: str, **kwargs) -> Optional[TravelPlace]:
        return None

    async def autocomplete_places(self, **kwargs) -> List[TravelPlaceAutocompleteItem]:
        return []


def _filter_by_proximity(
    items: List[Dict[str, Any]],
    lat: float,
    lon: float,
    radius_km: float,
) -> List[Dict[str, Any]]:
    """Filter a list of AirLabs airport records by Haversine distance."""
    import math

    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    result = []
    for item in items:
        try:
            item_lat = float(item.get("lat", 0))
            item_lon = float(item.get("lng", 0))
            dist = haversine(lat, lon, item_lat, item_lon)
            if dist <= radius_km:
                item["_distance_km"] = round(dist, 1)
                result.append(item)
        except (TypeError, ValueError):
            continue

    return sorted(result, key=lambda x: x.get("_distance_km", 9999))
