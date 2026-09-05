"""Amadeus Travel Data Provider implementing flights, hotels, airports, and activities."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config.settings import settings
from backend.app.travel.normalizers.amadeus_normalizer import AmadeusNormalizer
from backend.app.travel.providers.base import TravelDataProvider
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)

logger = logging.getLogger("khojai.travel.providers.amadeus")


class AmadeusProvider(TravelDataProvider):
    """Official Amadeus Self-Service API Provider with token caching and resilience."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        super().__init__(provider_name="amadeus")
        self.client_id = client_id or settings.AMADEUS_CLIENT_ID
        self.client_secret = client_secret or settings.AMADEUS_CLIENT_SECRET
        self.base_url = (base_url or settings.AMADEUS_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.TRAVEL_API_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.TRAVEL_API_MAX_RETRIES

        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._lock = asyncio.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _get_valid_token(self) -> str:
        """Retrieve cached OAuth2 token or authenticate with Amadeus client credentials."""
        now = time.time()
        if self._access_token and self._token_expires_at > (now + 60):
            return self._access_token

        async with self._lock:
            # Double check after acquiring lock
            if self._access_token and self._token_expires_at > (time.time() + 60):
                return self._access_token

            token_url = f"{self.base_url}/v1/security/oauth2/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }

            logger.info("Authenticating with Amadeus OAuth2 API...")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    token_url,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if resp.status_code != 200:
                    logger.error(f"Amadeus authentication failed: {resp.status_code} - {resp.text}")
                    resp.raise_for_status()

                payload = resp.json()
                self._access_token = payload.get("access_token")
                expires_in = payload.get("expires_in", 1799)
                self._token_expires_at = time.time() + expires_in
                logger.info("Amadeus OAuth2 token acquired successfully.")
                return self._access_token

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute resilient HTTP request with token injection, timeout, retry, and rate-limit backoff."""
        token = await self._get_valid_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.base_url}{endpoint}"

        retries = 0
        while retries <= self.max_retries:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.request(method, url, headers=headers, params=params)

                    # Handle token expiry
                    if resp.status_code == 401 and retries < self.max_retries:
                        logger.warning("Amadeus token rejected (401). Refreshing token and retrying...")
                        self._access_token = None
                        token = await self._get_valid_token()
                        headers["Authorization"] = f"Bearer {token}"
                        retries += 1
                        continue

                    # Handle rate limit
                    if resp.status_code == 429:
                        wait_sec = 2.0 * (2**retries)
                        logger.warning(f"Amadeus rate limit (429) hit. Backing off for {wait_sec}s...")
                        await asyncio.sleep(wait_sec)
                        retries += 1
                        continue

                    resp.raise_for_status()
                    return resp.json()

            except (httpx.TimeoutException, httpx.NetworkError) as err:
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Amadeus API request timed out/failed after {self.max_retries} retries: {err}")
                    raise
                wait_sec = 1.0 * (2 ** (retries - 1))
                logger.warning(f"Amadeus network warning: {err}. Retrying in {wait_sec}s...")
                await asyncio.sleep(wait_sec)

        raise RuntimeError(f"Amadeus request failed after {self.max_retries} attempts.")

    async def search_hotels(
        self,
        city_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: int = 20,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelHotel]:
        if not self.is_configured:
            logger.warning("Amadeus credentials not configured. Skipping hotel search.")
            return []

        endpoint = "/v1/reference-data/locations/hotels/by-city"
        params: Dict[str, Any] = {}

        if city_code:
            params["cityCode"] = city_code.upper().strip()
        elif latitude is not None and longitude is not None:
            endpoint = "/v1/reference-data/locations/hotels/by-geocode"
            params["latitude"] = round(latitude, 4)
            params["longitude"] = round(longitude, 4)
            params["radius"] = radius_km
            params["radiusUnit"] = "KM"
        else:
            return []

        try:
            payload = await self._request("GET", endpoint, params=params)
            hotels = AmadeusNormalizer.normalize_hotels(payload)
            return hotels[:limit]
        except Exception as e:
            logger.error(f"Amadeus hotel search error: {e}")
            raise

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
        if not self.is_configured:
            logger.warning("Amadeus credentials not configured. Skipping flight search.")
            return []

        params = {
            "originLocationCode": origin_code.upper().strip(),
            "destinationLocationCode": destination_code.upper().strip(),
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": "INR",
            "max": limit,
        }
        if return_date:
            params["returnDate"] = return_date

        try:
            payload = await self._request("GET", "/v2/shopping/flight-offers", params=params)
            return AmadeusNormalizer.normalize_flights(payload)
        except Exception as e:
            logger.error(f"Amadeus flight search error: {e}")
            raise

    async def search_activities(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 25,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelActivity]:
        if not self.is_configured:
            logger.warning("Amadeus credentials not configured. Skipping activities search.")
            return []

        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "radius": radius_km,
        }

        try:
            payload = await self._request("GET", "/v1/shopping/activities", params=params)
            activities = AmadeusNormalizer.normalize_activities(payload)
            return activities[:limit]
        except Exception as e:
            logger.error(f"Amadeus activities search error: {e}")
            raise

    async def search_airports(
        self,
        keyword: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit: int = 10,
        **kwargs,
    ) -> List[TravelAirport]:
        if not self.is_configured:
            return []

        try:
            if keyword:
                params = {
                    "subType": "AIRPORT,CITY",
                    "keyword": keyword.strip(),
                    "page[limit]": limit,
                }
                payload = await self._request("GET", "/v1/reference-data/locations", params=params)
            elif latitude is not None and longitude is not None:
                params = {
                    "latitude": round(latitude, 4),
                    "longitude": round(longitude, 4),
                    "radius": 200,
                    "page[limit]": limit,
                }
                payload = await self._request("GET", "/v1/reference-data/locations/airports", params=params)
            else:
                return []

            return AmadeusNormalizer.normalize_airports(payload)
        except Exception as e:
            logger.error(f"Amadeus airport search error: {e}")
            raise

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
        # Amadeus focuses on activities and hotels; places are delegated to Google Places or Local DB
        return []

    async def get_place_details(self, place_id: str, **kwargs) -> Optional[TravelPlace]:
        return None

    async def autocomplete_places(
        self,
        input_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 50000,
        **kwargs,
    ) -> List[TravelPlaceAutocompleteItem]:
        return []
