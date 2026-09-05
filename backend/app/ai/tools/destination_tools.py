import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select, or_, func
from backend.app.ai.tools.base import BaseTool, DataProvenance, ToolResult
from backend.app.database.session import async_session_factory
from backend.app.models import (
    Destination,
    Attraction,
    Activity,
    Hotel,
    Restaurant,
    City,
    State,
)
from backend.app.travel.services.travel_provider_service import TravelProviderService

logger = logging.getLogger(__name__)


class SearchDestinationsTool(BaseTool):
    """Tool to search curated travel destinations."""

    name = "search_destinations"
    description = (
        "Search curated travel destinations by keyword, region, tags, budget, or travel style. "
        "Returns destination summaries, highlights, ideal seasons, and key attributes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Destination search term or query (e.g. 'Rajasthan', 'Spiti', 'beaches in Kerala').",
            },
            "category": {
                "type": "string",
                "description": "Category filter (e.g. 'heritage', 'mountains', 'wildlife', 'spiritual', 'culture').",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of destinations to return (default 5).",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, category: Optional[str] = None, limit: int = 5, **kwargs) -> ToolResult:
        limit = min(max(1, limit), 20)
        query_term = query.strip()

        async with async_session_factory() as session:
            stmt = select(Destination).where(Destination.is_deleted.is_(False))

            filters = [
                Destination.name.ilike(f"%{query_term}%"),
                Destination.state.ilike(f"%{query_term}%"),
                Destination.country.ilike(f"%{query_term}%"),
                Destination.description.ilike(f"%{query_term}%"),
                Destination.short_description.ilike(f"%{query_term}%"),
            ]
            stmt = stmt.where(or_(*filters))

            if category:
                stmt = stmt.where(
                    or_(
                        Destination.category.ilike(f"%{category}%"),
                        Destination.tags.any(category.lower()),
                    )
                )

            stmt = stmt.order_by(Destination.rating.desc().nullslast()).limit(limit)
            res = await session.execute(stmt)
            destinations = res.scalars().all()

            results = []
            for d in destinations:
                results.append({
                    "id": str(d.id),
                    "name": d.name,
                    "state": d.state,
                    "country": d.country,
                    "description": d.short_description or d.description[:200] if d.description else None,
                    "category": d.category,
                    "tags": d.tags or [],
                    "best_time_to_visit": d.best_time_to_visit,
                    "budget_tier": d.budget_tier,
                    "rating": float(d.rating) if d.rating else None,
                    "latitude": float(d.latitude) if d.latitude else None,
                    "longitude": float(d.longitude) if d.longitude else None,
                })

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=results,
                message=f"Found {len(results)} destination(s) matching '{query}'.",
                provenance=DataProvenance.LOCAL_DATABASE,
                is_live_data=False,
                metadata={"query": query, "count": len(results)},
            )


class SearchAttractionsTool(BaseTool):
    """Tool to search tourist attractions and landmarks."""

    name = "search_attractions"
    description = (
        "Search tourist attractions, cultural sites, monuments, and natural landmarks by destination name or keyword."
    )
    parameters = {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Name of the destination or city (e.g. 'Jaipur', 'Varanasi', 'Kolkata').",
            },
            "category": {
                "type": "string",
                "description": "Attraction type filter (e.g. 'monument', 'museum', 'temple', 'nature', 'fort').",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of attractions to return (default 5).",
                "default": 5,
            },
        },
        "required": ["destination"],
    }

    async def execute(self, destination: str, category: Optional[str] = None, limit: int = 5, **kwargs) -> ToolResult:
        limit = min(max(1, limit), 20)
        dest_term = destination.strip()

        async with async_session_factory() as session:
            stmt = select(Attraction).join(Attraction.city, isouter=True)
            stmt = stmt.where(
                or_(
                    Attraction.name.ilike(f"%{dest_term}%"),
                    Attraction.address.ilike(f"%{dest_term}%"),
                    City.name.ilike(f"%{dest_term}%"),
                )
            )
            if category:
                stmt = stmt.where(Attraction.category.ilike(f"%{category}%"))

            stmt = stmt.order_by(Attraction.rating.desc().nullslast()).limit(limit)
            res = await session.execute(stmt)
            attractions = res.scalars().all()

            results = []
            for a in attractions:
                results.append({
                    "id": str(a.id),
                    "name": a.name,
                    "city": a.city.name if a.city else None,
                    "category": a.category,
                    "description": a.description,
                    "rating": float(a.rating) if a.rating else None,
                    "estimated_duration_hours": float(a.estimated_duration_hours) if a.estimated_duration_hours else None,
                    "admission_fee_estimate": float(a.admission_fee) if a.admission_fee else None,
                    "fee_currency": a.admission_currency or "INR",
                    "opening_hours_note": "Reference hours only; verify locally before visiting." if a.opening_hours else None,
                    "latitude": float(a.latitude) if a.latitude else None,
                    "longitude": float(a.longitude) if a.longitude else None,
                })

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=results,
                message=f"Found {len(results)} attraction(s) in/near '{destination}'.",
                provenance=DataProvenance.LOCAL_DATABASE,
                is_live_data=False,
                metadata={"destination": destination, "count": len(results)},
            )


class SearchActivitiesTool(BaseTool):
    """Tool to search travel experiences, activities, and tours."""

    name = "search_activities"
    description = (
        "Search tours, outdoor adventures, cultural workshops, and guided experiences for a given destination."
    )
    parameters = {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Destination or city name (e.g. 'Manali', 'Goa', 'Jaipur').",
            },
            "latitude": {
                "type": "number",
                "description": "Optional latitude coordinates for geographic lookup.",
            },
            "longitude": {
                "type": "number",
                "description": "Optional longitude coordinates for geographic lookup.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum activities to return (default 5).",
                "default": 5,
            },
        },
        "required": ["destination"],
    }

    def __init__(self, provider_service: Optional[TravelProviderService] = None):
        self.provider_service = provider_service or TravelProviderService()

    async def execute(
        self,
        destination: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit: int = 5,
        **kwargs,
    ) -> ToolResult:
        limit = min(max(1, limit), 20)

        # 1. Attempt Amadeus / TravelProviderService if coordinates available
        activities = []
        is_live = False
        if latitude and longitude and self.provider_service.amadeus.is_configured:
            try:
                activities = await self.provider_service.get_activities(
                    latitude=latitude, longitude=longitude, limit=limit
                )
                if activities:
                    is_live = True
            except Exception as exc:
                logger.warning(f"Live activity search failed: {exc}")

        # 2. Query Local Database activities
        if not activities:
            async with async_session_factory() as session:
                stmt = select(Activity).join(Activity.city, isouter=True)
                stmt = stmt.where(
                    or_(
                        Activity.name.ilike(f"%{destination}%"),
                        Activity.description.ilike(f"%{destination}%"),
                        City.name.ilike(f"%{destination}%"),
                    )
                ).limit(limit)
                res = await session.execute(stmt)
                db_activities = res.scalars().all()
                activities = [
                    {
                        "id": str(act.id),
                        "name": act.name,
                        "description": act.description,
                        "category": act.category,
                        "duration_hours": float(act.duration_hours) if act.duration_hours else None,
                        "price_estimate": float(act.price_estimate) if act.price_estimate else None,
                        "currency": act.currency or "INR",
                        "booking_link": act.booking_url,
                        "rating": float(act.rating) if act.rating else None,
                    }
                    for act in db_activities
                ]

        formatted_data = [
            act.model_dump() if hasattr(act, "model_dump") else act
            for act in activities
        ]

        provenance = DataProvenance.LIVE_API if is_live else DataProvenance.LOCAL_DATABASE
        return ToolResult(
            tool_name=self.name,
            success=True,
            data=formatted_data,
            message=f"Found {len(formatted_data)} activities for '{destination}'.",
            provenance=provenance,
            is_live_data=is_live,
            metadata={"destination": destination, "count": len(formatted_data)},
        )


class SearchLocalDatabaseTool(BaseTool):
    """Tool to perform hybrid search across the local database."""

    name = "search_local_database"
    description = (
        "Search across all local travel tables (destinations, attractions, hotels, restaurants, tips) "
        "for comprehensive offline-verified travel knowledge."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "General search query across all local travel data.",
            },
            "limit_per_category": {
                "type": "integer",
                "description": "Maximum items per category to return (default 3).",
                "default": 3,
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, limit_per_category: int = 3, **kwargs) -> ToolResult:
        query_term = query.strip()
        limit = min(max(1, limit_per_category), 10)

        results: Dict[str, List[Any]] = {
            "destinations": [],
            "attractions": [],
            "hotels": [],
            "restaurants": [],
        }

        async with async_session_factory() as session:
            # Destinations
            d_res = await session.execute(
                select(Destination)
                .where(
                    Destination.is_deleted.is_(False),
                    or_(
                        Destination.name.ilike(f"%{query_term}%"),
                        Destination.state.ilike(f"%{query_term}%"),
                        Destination.description.ilike(f"%{query_term}%"),
                    ),
                )
                .limit(limit)
            )
            results["destinations"] = [
                {"name": d.name, "state": d.state, "category": d.category, "rating": float(d.rating) if d.rating else None}
                for d in d_res.scalars().all()
            ]

            # Attractions
            a_res = await session.execute(
                select(Attraction)
                .where(
                    or_(
                        Attraction.name.ilike(f"%{query_term}%"),
                        Attraction.description.ilike(f"%{query_term}%"),
                    )
                )
                .limit(limit)
            )
            results["attractions"] = [
                {"name": a.name, "category": a.category, "rating": float(a.rating) if a.rating else None}
                for a in a_res.scalars().all()
            ]

            # Hotels
            h_res = await session.execute(
                select(Hotel)
                .where(
                    or_(
                        Hotel.name.ilike(f"%{query_term}%"),
                        Hotel.description.ilike(f"%{query_term}%"),
                    )
                )
                .limit(limit)
            )
            results["hotels"] = [
                {"name": h.name, "rating": float(h.rating) if h.rating else None, "price_tier": h.price_range}
                for h in h_res.scalars().all()
            ]

            # Restaurants
            r_res = await session.execute(
                select(Restaurant)
                .where(
                    or_(
                        Restaurant.name.ilike(f"%{query_term}%"),
                        Restaurant.cuisine_types.any(query_term.lower()),
                    )
                )
                .limit(limit)
            )
            results["restaurants"] = [
                {"name": r.name, "rating": float(r.rating) if r.rating else None, "price_tier": r.price_range}
                for r in r_res.scalars().all()
            ]

        total_items = sum(len(v) for v in results.values())
        return ToolResult(
            tool_name=self.name,
            success=True,
            data=results,
            message=f"Local database query returned {total_items} items across categories.",
            provenance=DataProvenance.LOCAL_DATABASE,
            is_live_data=False,
            metadata={"query": query, "total_found": total_items},
        )
