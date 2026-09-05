import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select, or_
from backend.app.ai.tools.base import BaseTool, DataProvenance, ToolResult
from backend.app.database.session import async_session_factory
from backend.app.models import Hotel, Restaurant, Airport, City
from backend.app.travel.services.travel_provider_service import TravelProviderService

logger = logging.getLogger(__name__)


# Known Indian city to IATA airport code mapping for instant resolution
CITY_TO_IATA = {
    "delhi": "DEL",
    "new delhi": "DEL",
    "mumbai": "BOM",
    "bombay": "BOM",
    "kolkata": "CCU",
    "calcutta": "CCU",
    "bengaluru": "BLR",
    "bangalore": "BLR",
    "chennai": "MAA",
    "madras": "MAA",
    "hyderabad": "HYD",
    "jaipur": "JAI",
    "goa": "GOI",
    "ahmedabad": "AMD",
    "kochi": "COK",
    "cochin": "COK",
    "varanasi": "VNS",
    "pune": "PNQ",
    "srinagar": "SXR",
    "guwahati": "GAU",
    "amritsar": "ATQ",
    "lucknow": "LKO",
    "chandigarh": "IXC",
    "udaipur": "UDR",
    "jodhpur": "JDH",
    "bhubaneswar": "BBI",
    "patna": "PAT",
    "dehradun": "DED",
    "bagdogra": "IXB",
    "port blair": "IXZ",
}


class SearchHotelsTool(BaseTool):
    """Tool to search hotels and accommodations."""

    name = "search_hotels"
    description = (
        "Search hotels, boutique homestays, and accommodations by city name or IATA code. "
        "Returns hotel names, ratings, location coordinates, amenities, and price tier."
    )
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City or destination name (e.g. 'Jaipur', 'Udaipur', 'Goa', 'DEL').",
            },
            "latitude": {
                "type": "number",
                "description": "Optional latitude for radius lookup.",
            },
            "longitude": {
                "type": "number",
                "description": "Optional longitude for radius lookup.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of hotels to return (default 5).",
                "default": 5,
            },
        },
        "required": ["city"],
    }

    def __init__(self, provider_service: Optional[TravelProviderService] = None):
        self.provider_service = provider_service or TravelProviderService()

    async def execute(
        self,
        city: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit: int = 5,
        **kwargs,
    ) -> ToolResult:
        limit = min(max(1, limit), 20)
        clean_city = city.strip()
        city_code = CITY_TO_IATA.get(clean_city.lower(), clean_city.upper() if len(clean_city) == 3 else None)

        hotels = await self.provider_service.get_hotels(
            city_code=city_code,
            latitude=latitude,
            longitude=longitude,
            limit=limit,
        )

        formatted = [h.model_dump() for h in hotels]
        is_live = any(h.provider == "amadeus" for h in hotels)
        provenance = DataProvenance.LIVE_API if is_live else DataProvenance.LOCAL_DATABASE

        warning = None
        if not is_live:
            warning = (
                "Real-time live hotel availability and live rack rates are currently unavailable. "
                "The listings provided reflect verified directory reference data and indicative price tiers."
            )

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=formatted,
            message=f"Found {len(formatted)} hotel(s) in/near '{city}'.",
            provenance=provenance,
            is_live_data=is_live,
            warning=warning,
            metadata={"city": city, "count": len(formatted), "is_live": is_live},
        )


class SearchRestaurantsTool(BaseTool):
    """Tool to search restaurants and regional culinary spots."""

    name = "search_restaurants"
    description = (
        "Search restaurants, traditional dhabas, local cafes, and dining spots by city or cuisine type."
    )
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City or area name (e.g. 'Jaipur', 'Old Delhi', 'Kolkata').",
            },
            "cuisine": {
                "type": "string",
                "description": "Optional cuisine type (e.g. 'Rajasthani', 'Bengali', 'Mughlai', 'Vegetarian').",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum restaurants to return (default 5).",
                "default": 5,
            },
        },
        "required": ["city"],
    }

    async def execute(self, city: str, cuisine: Optional[str] = None, limit: int = 5, **kwargs) -> ToolResult:
        limit = min(max(1, limit), 20)
        clean_city = city.strip()

        async with async_session_factory() as session:
            stmt = select(Restaurant).join(Restaurant.city, isouter=True)
            stmt = stmt.where(
                or_(
                    Restaurant.name.ilike(f"%{clean_city}%"),
                    Restaurant.address.ilike(f"%{clean_city}%"),
                    City.name.ilike(f"%{clean_city}%"),
                )
            )
            if cuisine:
                stmt = stmt.where(
                    or_(
                        Restaurant.cuisine_types.any(cuisine.lower()),
                        Restaurant.description.ilike(f"%{cuisine}%"),
                    )
                )

            stmt = stmt.order_by(Restaurant.rating.desc().nullslast()).limit(limit)
            res = await session.execute(stmt)
            restaurants = res.scalars().all()

            results = []
            for r in restaurants:
                results.append({
                    "id": str(r.id),
                    "name": r.name,
                    "city": r.city.name if r.city else None,
                    "cuisine_types": r.cuisine_types or [],
                    "price_range": r.price_range,
                    "rating": float(r.rating) if r.rating else None,
                    "address": r.address,
                    "phone": r.phone,
                    "opening_hours_note": "Reference hours only; verify locally before dining." if r.opening_hours else None,
                })

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=results,
                message=f"Found {len(results)} restaurant(s) in '{city}'.",
                provenance=DataProvenance.LOCAL_DATABASE,
                is_live_data=False,
                warning="Live table availability is not verified; hours and pricing are reference estimates.",
                metadata={"city": city, "count": len(results)},
            )


class SearchFlightsTool(BaseTool):
    """Tool to search flights between two airports/cities."""

    name = "search_flights"
    description = (
        "Search scheduled flight offers between origin and destination cities or IATA airport codes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "Origin city or IATA code (e.g. 'Kolkata', 'CCU', 'DEL').",
            },
            "destination": {
                "type": "string",
                "description": "Destination city or IATA code (e.g. 'Delhi', 'DEL', 'BOM').",
            },
            "departure_date": {
                "type": "string",
                "description": "Departure date in YYYY-MM-DD format (optional).",
            },
            "adults": {
                "type": "integer",
                "description": "Number of adult passengers (default 1).",
                "default": 1,
            },
        },
        "required": ["origin", "destination"],
    }

    def __init__(self, provider_service: Optional[TravelProviderService] = None):
        self.provider_service = provider_service or TravelProviderService()

    async def execute(
        self,
        origin: str,
        destination: str,
        departure_date: Optional[str] = None,
        adults: int = 1,
        **kwargs,
    ) -> ToolResult:
        from datetime import datetime, timezone, timedelta

        orig_code = CITY_TO_IATA.get(origin.strip().lower(), origin.strip().upper())
        dest_code = CITY_TO_IATA.get(destination.strip().lower(), destination.strip().upper())
        dep_date = departure_date or (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

        flights = await self.provider_service.get_flights(
            origin_code=orig_code,
            destination_code=dest_code,
            departure_date=dep_date,
            adults=adults,
        )

        formatted = [f.model_dump() for f in flights]
        is_live = any(f.provider == "amadeus" for f in flights)

        warning = None
        if not is_live:
            warning = (
                "Real-time airline GDS booking confirmation is currently offline. "
                "Typical schedule routes and historical fare estimates are provided; live seats and dynamic pricing are not guaranteed."
            )

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=formatted,
            message=f"Found {len(formatted)} flight route(s) from {origin} ({orig_code}) to {destination} ({dest_code}).",
            provenance=DataProvenance.LIVE_API if is_live else DataProvenance.ESTIMATE_RECOMMENDATION,
            is_live_data=is_live,
            warning=warning,
            metadata={"origin": orig_code, "destination": dest_code, "is_live": is_live},
        )


class SearchAirportsTool(BaseTool):
    """Tool to search airports by city name or IATA code."""

    name = "search_airports"
    description = (
        "Search airports by city name or IATA code to resolve flight hubs, terminal locations, and distances."
    )
    parameters = {
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "City name or airport keyword (e.g. 'Jaipur', 'Delhi', 'CCU').",
            },
        },
        "required": ["keyword"],
    }

    def __init__(self, provider_service: Optional[TravelProviderService] = None):
        self.provider_service = provider_service or TravelProviderService()

    async def execute(self, keyword: str, **kwargs) -> ToolResult:
        airports = await self.provider_service.get_airports(keyword=keyword)
        formatted = [a.model_dump() for a in airports]

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=formatted,
            message=f"Resolved {len(formatted)} airport(s) for '{keyword}'.",
            provenance=DataProvenance.LOCAL_DATABASE,
            is_live_data=False,
            metadata={"keyword": keyword, "count": len(formatted)},
        )
