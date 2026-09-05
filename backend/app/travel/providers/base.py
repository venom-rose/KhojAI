"""Abstract base class for all travel data providers in KHOJAI."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)


class TravelDataProvider(ABC):
    """Unified adapter interface for travel data providers (Amadeus, Google Places, Local DB)."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has all necessary API keys and credentials."""
        pass

    @abstractmethod
    async def search_hotels(
        self,
        city_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: int = 20,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelHotel]:
        """Search hotels by city code (IATA) or geographic coordinates."""
        pass

    @abstractmethod
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
        """Search flight offers between airports/cities."""
        pass

    @abstractmethod
    async def search_activities(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 25,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelActivity]:
        """Search tours, cultural workshops, and activities by coordinates."""
        pass

    @abstractmethod
    async def search_airports(
        self,
        keyword: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit: int = 10,
        **kwargs,
    ) -> List[TravelAirport]:
        """Search airports by keyword name/code or nearest coordinates."""
        pass

    @abstractmethod
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
        """Search places or attractions by text query or nearby coordinates."""
        pass

    @abstractmethod
    async def get_place_details(self, place_id: str, **kwargs) -> Optional[TravelPlace]:
        """Retrieve detailed place information including reviews, hours, and contacts."""
        pass

    @abstractmethod
    async def autocomplete_places(
        self,
        input_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 50000,
        **kwargs,
    ) -> List[TravelPlaceAutocompleteItem]:
        """Predictive search autocomplete for destinations and landmarks."""
        pass
