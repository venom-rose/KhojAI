"""Travel Search Service coordinating unified multi-domain search across destinations, places, hotels, and activities."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelDestination,
    TravelHotel,
    TravelPlace,
)
from backend.app.travel.services.destination_service import DestinationService
from backend.app.travel.services.hotel_service import HotelService
from backend.app.travel.services.activity_service import ActivityService
from backend.app.travel.services.place_service import PlaceService

logger = logging.getLogger("khojai.travel.services.travel_search")


class UnifiedTravelSearchResult(BaseModel):
    """Aggregated search result containing multiple travel domains."""
    query: str
    destinations: List[TravelDestination] = Field(default_factory=list)
    places: List[TravelPlace] = Field(default_factory=list)
    hotels: List[TravelHotel] = Field(default_factory=list)
    activities: List[TravelActivity] = Field(default_factory=list)
    total_count: int = 0


class TravelSearchService:
    """Orchestrates concurrent searches across travel domains."""

    def __init__(
        self,
        destination_service: Optional[DestinationService] = None,
        hotel_service: Optional[HotelService] = None,
        activity_service: Optional[ActivityService] = None,
        place_service: Optional[PlaceService] = None,
    ):
        self.destinations = destination_service or DestinationService()
        self.hotels = hotel_service or HotelService()
        self.activities = activity_service or ActivityService()
        self.places = place_service or PlaceService()

    async def search_all(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit_per_category: int = 5,
    ) -> UnifiedTravelSearchResult:
        """Concurrent multi-domain search across destinations, places, hotels, and activities."""
        clean_q = query.strip() if query else ""

        # Launch searches concurrently
        async def _get_destinations():
            try:
                return await self.destinations.search_destinations(query=clean_q, limit=limit_per_category)
            except Exception as e:
                logger.error(f"Error fetching destinations for '{clean_q}': {e}")
                return []

        async def _get_places():
            try:
                return await self.places.search_places(
                    query=clean_q,
                    latitude=latitude,
                    longitude=longitude,
                    limit=limit_per_category,
                )
            except Exception as e:
                logger.error(f"Error fetching places for '{clean_q}': {e}")
                return []

        async def _get_hotels():
            try:
                return await self.hotels.search_hotels(
                    city_code=clean_q[:3].upper() if len(clean_q) == 3 else None,
                    latitude=latitude,
                    longitude=longitude,
                    limit=limit_per_category,
                )
            except Exception as e:
                logger.error(f"Error fetching hotels for '{clean_q}': {e}")
                return []

        async def _get_activities():
            if latitude is not None and longitude is not None:
                try:
                    return await self.activities.search_activities(
                        latitude=latitude,
                        longitude=longitude,
                        limit=limit_per_category,
                    )
                except Exception as e:
                    logger.error(f"Error fetching activities for '{clean_q}': {e}")
            return []

        dest_res, place_res, hotel_res, act_res = await asyncio.gather(
            _get_destinations(),
            _get_places(),
            _get_hotels(),
            _get_activities(),
            return_exceptions=False,
        )

        total = len(dest_res) + len(place_res) + len(hotel_res) + len(act_res)

        return UnifiedTravelSearchResult(
            query=clean_q,
            destinations=dest_res,
            places=place_res,
            hotels=hotel_res,
            activities=act_res,
            total_count=total,
        )
