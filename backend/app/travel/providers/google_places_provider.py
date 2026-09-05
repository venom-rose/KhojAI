"""Google Places API (New) Provider implementing search, details, autocomplete, and photo proxy."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config.settings import settings
from backend.app.travel.normalizers.google_normalizer import GooglePlacesNormalizer
from backend.app.travel.providers.base import TravelDataProvider
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)

logger = logging.getLogger("khojai.travel.providers.google_places")


class GooglePlacesProvider(TravelDataProvider):
    """Google Places API (New) adapter with field masking and key isolation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        super().__init__(provider_name="google_places")
        self.api_key = api_key or settings.GOOGLE_MAPS_API_KEY
        self.base_url = "https://places.googleapis.com/v1"
        self.timeout = timeout or settings.TRAVEL_API_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.TRAVEL_API_MAX_RETRIES

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

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
        if not self.is_configured:
            logger.warning("Google Maps API key not configured. Skipping Google Places search.")
            return []

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,places.location,"
                "places.rating,places.userRatingCount,places.priceLevel,places.types,"
                "places.photos,places.regularOpeningHours,places.businessStatus"
            ),
        }

        # Nearby search vs Text search
        if latitude is not None and longitude is not None and not query:
            url = f"{self.base_url}/places:searchNearby"
            body: Dict[str, Any] = {
                "maxResultCount": limit,
                "locationRestriction": {
                    "circle": {
                        "center": {"latitude": latitude, "longitude": longitude},
                        "radius": float(radius_meters),
                    }
                },
            }
            if included_types:
                body["includedTypes"] = included_types
        else:
            url = f"{self.base_url}/places:searchText"
            body = {
                "textQuery": query,
                "pageSize": limit,
            }
            if latitude is not None and longitude is not None:
                body["locationBias"] = {
                    "circle": {
                        "center": {"latitude": latitude, "longitude": longitude},
                        "radius": float(radius_meters),
                    }
                }
            if included_types:
                body["includedType"] = included_types[0]

        retries = 0
        while retries <= self.max_retries:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=body, headers=headers)
                    if resp.status_code == 429:
                        wait = 2.0 * (2**retries)
                        logger.warning(f"Google Places rate limit (429). Retrying in {wait}s...")
                        await asyncio.sleep(wait)
                        retries += 1
                        continue

                    resp.raise_for_status()
                    payload = resp.json()
                    return GooglePlacesNormalizer.normalize_places(payload)
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Google Places search failed: {e}")
                    raise
                await asyncio.sleep(1.0 * (2 ** (retries - 1)))

        return []

    async def get_place_details(self, place_id: str, **kwargs) -> Optional[TravelPlace]:
        if not self.is_configured:
            return None

        # Format URL: places/{placeId}
        clean_id = place_id.split("/")[-1]
        url = f"{self.base_url}/places/{clean_id}"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "id,displayName,formattedAddress,location,rating,userRatingCount,"
                "priceLevel,types,photos,regularOpeningHours,websiteUri,nationalPhoneNumber,reviews"
            ),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                payload = resp.json()
                return GooglePlacesNormalizer.normalize_single_place(payload)
        except Exception as e:
            logger.error(f"Google Place details error for {place_id}: {e}")
            raise

    async def autocomplete_places(
        self,
        input_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 50000,
        **kwargs,
    ) -> List[TravelPlaceAutocompleteItem]:
        if not self.is_configured or not input_text:
            return []

        url = f"{self.base_url}/places:autocomplete"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
        }
        body: Dict[str, Any] = {
            "input": input_text,
            "includedRegionCodes": ["IN"],
        }
        if latitude is not None and longitude is not None:
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": float(radius_meters),
                }
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=body, headers=headers)
                resp.raise_for_status()
                payload = resp.json()
                return GooglePlacesNormalizer.normalize_autocomplete(payload)
        except Exception as e:
            logger.error(f"Google Places autocomplete error: {e}")
            raise

    async def fetch_photo_bytes(
        self,
        photo_name: str,
        max_height_px: int = 800,
        max_width_px: int = 1200,
    ) -> Optional[tuple[bytes, str]]:
        """Fetch raw photo binary bytes from Google Places API for backend proxying.

        Ensures GOOGLE_MAPS_API_KEY is NEVER exposed to the frontend.
        """
        if not self.is_configured or not photo_name:
            return None

        # Clean photo name
        clean_name = photo_name.lstrip("/")
        url = f"{self.base_url}/{clean_name}/media"
        params = {
            "key": self.api_key,
            "maxHeightPx": max_height_px,
            "maxWidthPx": max_width_px,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "image/jpeg")
                return (resp.content, content_type)
        except Exception as e:
            logger.error(f"Google Places photo proxy error: {e}")
            return None

    # Unimplemented by Google Places (delegated to Amadeus / Local DB)
    async def search_hotels(self, **kwargs) -> List[TravelHotel]:
        return []

    async def search_flights(self, **kwargs) -> List[TravelFlight]:
        return []

    async def search_activities(self, **kwargs) -> List[TravelActivity]:
        return []

    async def search_airports(self, **kwargs) -> List[TravelAirport]:
        return []
