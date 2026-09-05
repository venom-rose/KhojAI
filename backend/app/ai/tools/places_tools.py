import logging
from typing import Any, Dict, List, Optional
from backend.app.ai.tools.base import BaseTool, DataProvenance, ToolResult
from backend.app.travel.services.travel_provider_service import TravelProviderService

logger = logging.getLogger(__name__)


class SearchPlacesTool(BaseTool):
    """Tool to search geographic places, landmarks, and points of interest."""

    name = "search_places"
    description = (
        "Search geographic points of interest, tourist spots, cultural landmarks, or neighborhood centers "
        "using Google Places API (New) or offline database fallback."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Place search query (e.g. 'Hawa Mahal Jaipur', 'cafes in Fort Kochi', 'stepwells in Bundi').",
            },
            "latitude": {
                "type": "number",
                "description": "Optional center latitude for nearby ranking.",
            },
            "longitude": {
                "type": "number",
                "description": "Optional center longitude for nearby ranking.",
            },
            "radius_meters": {
                "type": "integer",
                "description": "Search radius in meters if coordinates are provided (default 10000).",
                "default": 10000,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of places to return (default 5).",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(self, provider_service: Optional[TravelProviderService] = None):
        self.provider_service = provider_service or TravelProviderService()

    async def execute(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 10000,
        limit: int = 5,
        **kwargs,
    ) -> ToolResult:
        places = await self.provider_service.get_places(
            query=query,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            limit=limit,
        )

        formatted = [p.model_dump() for p in places]
        is_live = any(p.provider == "google_places" for p in places)

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=formatted,
            message=f"Found {len(formatted)} place(s) matching '{query}'.",
            provenance=DataProvenance.LIVE_API if is_live else DataProvenance.LOCAL_DATABASE,
            is_live_data=is_live,
            metadata={"query": query, "count": len(formatted), "is_live": is_live},
        )


class GetPlaceDetailsTool(BaseTool):
    """Tool to retrieve comprehensive details for a specific place."""

    name = "get_place_details"
    description = (
        "Retrieve in-depth information about a specific place or attraction, including full address, "
        "contact phone, editorial summary, ratings, and operating hours."
    )
    parameters = {
        "type": "object",
        "properties": {
            "place_id": {
                "type": "string",
                "description": "Unique Google Place ID or internal local place ID.",
            },
        },
        "required": ["place_id"],
    }

    def __init__(self, provider_service: Optional[TravelProviderService] = None):
        self.provider_service = provider_service or TravelProviderService()

    async def execute(self, place_id: str, **kwargs) -> ToolResult:
        place = await self.provider_service.get_place_details(place_id=place_id)

        if not place:
            return ToolResult(
                tool_name=self.name,
                success=False,
                data=None,
                message=f"Place details for '{place_id}' could not be located.",
                provenance=DataProvenance.LOCAL_DATABASE,
                is_live_data=False,
            )

        data = place.model_dump()
        is_live = place.provider == "google_places"

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=data,
            message=f"Retrieved details for '{place.name}'.",
            provenance=DataProvenance.LIVE_API if is_live else DataProvenance.LOCAL_DATABASE,
            is_live_data=is_live,
            metadata={"place_id": place_id, "is_live": is_live},
        )
