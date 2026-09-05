from backend.app.ai.tools.base import BaseTool, DataProvenance, ToolResult
from backend.app.ai.tools.registry import ToolRegistry, default_tool_registry

from backend.app.ai.tools.destination_tools import (
    SearchDestinationsTool,
    SearchAttractionsTool,
    SearchActivitiesTool,
    SearchLocalDatabaseTool,
)
from backend.app.ai.tools.booking_tools import (
    SearchHotelsTool,
    SearchRestaurantsTool,
    SearchFlightsTool,
    SearchAirportsTool,
)
from backend.app.ai.tools.places_tools import (
    SearchPlacesTool,
    GetPlaceDetailsTool,
)
from backend.app.ai.tools.geo_weather_tools import (
    GetWeatherTool,
    CalculateDistanceTool,
    CalculateRouteTool,
)
from backend.app.ai.tools.trip_tools import (
    GetUserPreferencesTool,
    CreateItineraryTool,
    SaveTripTool,
    RetrieveTripTool,
)


def register_all_tools(registry: ToolRegistry) -> None:
    """Register all standard travel tools into the given registry."""
    tools = [
        SearchDestinationsTool(),
        SearchAttractionsTool(),
        SearchActivitiesTool(),
        SearchHotelsTool(),
        SearchRestaurantsTool(),
        SearchFlightsTool(),
        SearchAirportsTool(),
        SearchPlacesTool(),
        GetPlaceDetailsTool(),
        GetWeatherTool(),
        CalculateDistanceTool(),
        CalculateRouteTool(),
        SearchLocalDatabaseTool(),
        GetUserPreferencesTool(),
        CreateItineraryTool(),
        SaveTripTool(),
        RetrieveTripTool(),
    ]
    for tool in tools:
        registry.register(tool)


# Initialize default tools
register_all_tools(default_tool_registry)

__all__ = [
    "BaseTool",
    "ToolResult",
    "DataProvenance",
    "ToolRegistry",
    "default_tool_registry",
    "register_all_tools",
    # Specific tool classes
    "SearchDestinationsTool",
    "SearchAttractionsTool",
    "SearchActivitiesTool",
    "SearchHotelsTool",
    "SearchRestaurantsTool",
    "SearchFlightsTool",
    "SearchAirportsTool",
    "SearchPlacesTool",
    "GetPlaceDetailsTool",
    "GetWeatherTool",
    "CalculateDistanceTool",
    "CalculateRouteTool",
    "SearchLocalDatabaseTool",
    "GetUserPreferencesTool",
    "CreateItineraryTool",
    "SaveTripTool",
    "RetrieveTripTool",
]
