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
                Destination.region.ilike(f"%{query_term}%"),
                Destination.description.ilike(f"%{query_term}%"),
                Destination.category.ilike(f"%{query_term}%"),
            ]
            stmt = stmt.where(or_(*filters))

            if category:
                stmt = stmt.where(
                    or_(
                        Destination.category.ilike(f"%{category}%"),
                        Destination.region.ilike(f"%{category}%"),
                    )
                )

            stmt = stmt.order_by(Destination.trust_score.desc().nullslast()).limit(limit)
            res = await session.execute(stmt)
            destinations = res.scalars().all()

            results = []
            for d in destinations:
                results.append({
                    "id": str(d.id),
                    "name": d.name,
                    "state": d.state,
                    "region": d.region,
                    "category": d.category,
                    "best_season": d.best_season,
                    "budget": d.budget,
                    "trust_score": d.trust_score,
                    "description": d.description[:300] if d.description else None,
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
            stmt = (
                select(Attraction)
                .join(Attraction.city, isouter=True)
                .join(Attraction.destination, isouter=True)
            )
            stmt = stmt.where(
                or_(
                    Attraction.name.ilike(f"%{dest_term}%"),
                    Attraction.description.ilike(f"%{dest_term}%"),
                    City.name.ilike(f"%{dest_term}%"),
                    Destination.name.ilike(f"%{dest_term}%"),
                )
            )
            if category:
                stmt = stmt.where(Attraction.category.ilike(f"%{category}%"))

            stmt = stmt.order_by(Attraction.name.asc()).limit(limit)
            res = await session.execute(stmt)
            attractions = res.scalars().all()

            results = []
            for a in attractions:
                results.append({
                    "id": str(a.id),
                    "name": a.name,
                    "city": a.city.name if a.city else None,
                    "destination": a.destination.name if a.destination else None,
                    "category": a.category,
                    "description": a.description,
                    "timings": a.timings,
                    "entry_fee": a.entry_fee,
                    "difficulty": a.difficulty,
                    "recommended_duration_mins": a.recommended_duration_mins,
                    "tags": a.tags or [],
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
                stmt = (
                    select(Activity)
                    .join(Activity.city, isouter=True)
                    .join(Activity.destination, isouter=True)
                )
                stmt = stmt.where(
                    or_(
                        Activity.title.ilike(f"%{destination}%"),
                        Activity.activity_type.ilike(f"%{destination}%"),
                        Activity.description.ilike(f"%{destination}%"),
                        City.name.ilike(f"%{destination}%"),
                        Destination.name.ilike(f"%{destination}%"),
                    )
                ).limit(limit)
                res = await session.execute(stmt)
                db_activities = res.scalars().all()
                activities = [
                    {
                        "id": str(act.id),
                        "title": act.title,
                        "name": act.title,
                        "activity_type": act.activity_type,
                        "description": act.description,
                        "duration_hours": float(act.duration_hours) if act.duration_hours else None,
                        "price_range": act.price_range,
                        "seasonality": act.seasonality,
                        "guide_required": act.guide_required,
                        "latitude": float(act.latitude) if act.latitude else None,
                        "longitude": float(act.longitude) if act.longitude else None,
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
        "Search across all local travel tables (destinations, attractions, hotels, restaurants) "
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
                        Destination.region.ilike(f"%{query_term}%"),
                        Destination.description.ilike(f"%{query_term}%"),
                    ),
                )
                .limit(limit)
            )
            results["destinations"] = [
                {"name": d.name, "state": d.state, "region": d.region, "category": d.category, "budget": d.budget}
                for d in d_res.scalars().all()
            ]

            # Attractions
            a_res = await session.execute(
                select(Attraction)
                .where(
                    or_(
                        Attraction.name.ilike(f"%{query_term}%"),
                        Attraction.category.ilike(f"%{query_term}%"),
                        Attraction.description.ilike(f"%{query_term}%"),
                    )
                )
                .limit(limit)
            )
            results["attractions"] = [
                {"name": a.name, "category": a.category, "timings": a.timings, "entry_fee": a.entry_fee}
                for a in a_res.scalars().all()
            ]

            # Hotels
            h_res = await session.execute(
                select(Hotel)
                .where(
                    or_(
                        Hotel.name.ilike(f"%{query_term}%"),
                        Hotel.address.ilike(f"%{query_term}%"),
                        Hotel.stay_type.ilike(f"%{query_term}%"),
                    )
                )
                .limit(limit)
            )
            results["hotels"] = [
                {"name": h.name, "stay_type": h.stay_type, "rating": float(h.rating) if h.rating else None, "price_level": h.price_level}
                for h in h_res.scalars().all()
            ]

            # Restaurants
            r_res = await session.execute(
                select(Restaurant)
                .where(
                    or_(
                        Restaurant.name.ilike(f"%{query_term}%"),
                        Restaurant.cuisine_type.ilike(f"%{query_term}%"),
                        Restaurant.address.ilike(f"%{query_term}%"),
                    )
                )
                .limit(limit)
            )
            results["restaurants"] = [
                {"name": r.name, "cuisine_type": r.cuisine_type, "rating": float(r.rating) if r.rating else None, "price_range": r.price_range}
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
