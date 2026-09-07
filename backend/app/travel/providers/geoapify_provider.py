"""Geoapify Travel Data Provider implementing place search, details, and autocomplete."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config.settings import settings
from backend.app.travel.normalizers.hotel_normalizer import HotelNormalizer
from backend.app.travel.normalizers.place_normalizer import PlaceNormalizer
from backend.app.travel.providers.base import TravelDataProvider
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)

logger = logging.getLogger("khojai.travel.providers.geoapify")


class GeoapifyProvider(TravelDataProvider):
    """Geoapify Places and Geocoding API adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        super().__init__(provider_name="geoapify")
        self.api_key = api_key or getattr(settings, "GEOAPIFY_API_KEY", "")
        self.base_url = (base_url or getattr(settings, "GEOAPIFY_BASE_URL", "https://api.geoapify.com")).rstrip("/")
        self.timeout = timeout or settings.TRAVEL_API_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.TRAVEL_API_MAX_RETRIES

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute resilient HTTP GET request with retries and backoff."""
        if not self.is_configured:
            return {}

        params = params or {}
        params["apiKey"] = self.api_key
        url = f"{self.base_url}{endpoint}"

        retries = 0
        while retries <= self.max_retries:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(url, params=params)

                    if resp.status_code == 429:
                        wait = 2.0 * (2**retries)
                        logger.warning(f"Geoapify rate limit (429). Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        retries += 1
                        continue

                    resp.raise_for_status()
                    return resp.json()
            except Exception as err:
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Geoapify request failed after {self.max_retries} attempts: {err}")
                    raise
                await asyncio.sleep(1.0 * (2 ** (retries - 1)))

        return {}

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
        """Search places by text query or nearby coordinates/categories."""
        if not self.is_configured:
            return []

        params: Dict[str, Any] = {"limit": limit}

        if latitude is not None and longitude is not None:
            params["filter"] = f"circle:{longitude},{latitude},{radius_meters}"
            params["bias"] = f"proximity:{longitude},{latitude}"
            if included_types:
                params["categories"] = ",".join(included_types)
            else:
                params["categories"] = "tourism,catering,entertainment,accommodation"
            endpoint = "/v2/places"
        elif query:
            params["text"] = query
            if included_types:
                params["categories"] = ",".join(included_types)
            endpoint = "/v2/places"
        else:
            return []

        try:
            payload = await self._get(endpoint, params=params)
            features = payload.get("features", [])
            return [PlaceNormalizer.normalize_geoapify(f) for f in features]
        except Exception as e:
            logger.error(f"Geoapify place search error: {e}")
            return []

    async def get_place_details(self, place_id: str, **kwargs) -> Optional[TravelPlace]:
        """Retrieve place details by place_id."""
        if not self.is_configured or not place_id:
            return None

        try:
            payload = await self._get("/v2/place-details", params={"id": place_id})
            features = payload.get("features", [])
            if features:
                return PlaceNormalizer.normalize_geoapify(features[0])
            return None
        except Exception as e:
            logger.error(f"Geoapify place details error for {place_id}: {e}")
            return None

    async def autocomplete_places(
        self,
        input_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 50000,
        **kwargs,
    ) -> List[TravelPlaceAutocompleteItem]:
        """Predictive autocomplete for places and addresses."""
        if not self.is_configured or not input_text:
            return []

        params: Dict[str, Any] = {
            "text": input_text,
            "filter": "countrycode:in",
            "limit": 10,
        }
        if latitude is not None and longitude is not None:
            params["bias"] = f"proximity:{longitude},{latitude}"

        try:
            payload = await self._get("/v1/geocode/autocomplete", params=params)
            results = []
            for item in payload.get("features", []):
                props = item.get("properties", {})
                results.append(
                    TravelPlaceAutocompleteItem(
                        place_id=props.get("place_id") or str(props.get("osm_id", "")),
                        primary_text=props.get("name") or props.get("address_line1") or input_text,
                        secondary_text=props.get("address_line2") or props.get("formatted"),
                        full_text=props.get("formatted") or props.get("name", ""),
                        types=props.get("categories", []),
                        provider="geoapify",
                    )
                )
            return results
        except Exception as e:
            logger.error(f"Geoapify autocomplete error: {e}")
            return []

    async def search_hotels(
        self,
        city_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: int = 20,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelHotel]:
        """Search hotels using accommodation category filter."""
        if not self.is_configured:
            return []

        places = await self.search_places(
            query=f"Hotels in {city_code}" if city_code else "",
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_km * 1000,
            included_types=["accommodation.hotel", "accommodation"],
            limit=limit,
        )
        return [HotelNormalizer.from_dict({
            "name": p.name,
            "place_id": p.place_id,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "address": p.formatted_address,
            "rating": p.rating,
        }, provider="geoapify") for p in places]

    async def search_activities(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 25,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelActivity]:
        """Search activities using tourism/entertainment category filter."""
        if not self.is_configured:
            return []

        places = await self.search_places(
            query="",
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_km * 1000,
            included_types=["tourism.sights", "entertainment", "leisure"],
            limit=limit,
        )
        return [
            TravelActivity(
                title=p.name,
                description=p.formatted_address,
                latitude=p.latitude,
                longitude=p.longitude,
                rating=p.rating or 4.0,
                provider="geoapify",
                provider_id=p.place_id,
            )
            for p in places
        ]

    async def search_airports(self, **kwargs) -> List[TravelAirport]:
        return []

    async def search_flights(self, **kwargs) -> List[TravelFlight]:
        return []
