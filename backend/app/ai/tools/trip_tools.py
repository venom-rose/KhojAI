import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from backend.app.ai.tools.base import BaseTool, DataProvenance, ToolResult
from backend.app.database.session import async_session_factory
from backend.app.models.itinerary import Itinerary, ItineraryDay
from backend.app.models.user import User
from backend.app.travel.models.trip import UserTravelPreference, Trip

logger = logging.getLogger(__name__)


class GetUserPreferencesTool(BaseTool):
    """Tool to retrieve traveler preferences and past styles."""

    name = "get_user_preferences"
    description = (
        "Retrieve user travel preferences (pace, budget tier, preferred styles, dietary restrictions) "
        "to personalize trip plans and recommendations."
    )
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "Optional UUID of the user. If omitted or not found, standard default preferences are returned.",
            },
        },
    }

    async def execute(self, user_id: Optional[str] = None, **kwargs) -> ToolResult:
        prefs = {
            "pace": "Unhurried & culturally immersive",
            "preferred_travel_style": ["Heritage", "Culture", "Quiet Landscapes"],
            "budget_tier": "Mid-tier / Boutique homestays (₹2,500 - ₹5,000 / night)",
            "dietary_preferences": ["Local regional cuisine", "Vegetarian-friendly"],
            "group_type": "Solo / Couple",
        }

        if user_id:
            try:
                uid = uuid.UUID(user_id)
                async with async_session_factory() as session:
                    # Check User table preferences
                    u_stmt = select(User).where(User.id == uid)
                    u_res = await session.execute(u_stmt)
                    user = u_res.scalar_one_or_none()
                    if user and user.travel_preferences:
                        prefs.update(user.travel_preferences)

                    # Check UserTravelPreference table
                    utp_stmt = select(UserTravelPreference).where(UserTravelPreference.user_id == uid)
                    utp_res = await session.execute(utp_stmt)
                    utp = utp_res.scalar_one_or_none()
                    if utp:
                        prefs["budget_tier"] = utp.budget_tier or prefs["budget_tier"]
                        prefs["pace"] = utp.pace_preference or prefs["pace"]
                        if utp.preferred_activities:
                            prefs["preferred_activities"] = utp.preferred_activities
            except Exception as exc:
                logger.warning(f"Failed to lookup specific user preferences ({exc}); using defaults.")

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=prefs,
            message="User travel preferences retrieved.",
            provenance=DataProvenance.SYSTEM_STATE,
            is_live_data=True,
            metadata={"user_id": user_id},
        )


class CreateItineraryTool(BaseTool):
    """Tool to build structured multi-day travel plans."""

    name = "create_itinerary"
    description = (
        "Generate a structured, day-by-day travel itinerary with morning, afternoon, and evening activity slots, "
        "pacing suggestions, and transit tips."
    )
    parameters = {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Primary destination or region (e.g. 'Rajasthan', 'Jaipur', 'Meghalaya').",
            },
            "days": {
                "type": "integer",
                "description": "Number of days for the itinerary (e.g. 3, 5, 7).",
                "default": 5,
            },
            "travel_style": {
                "type": "string",
                "description": "Pace or theme (e.g. 'heritage', 'slow travel', 'budget', 'wildlife').",
                "default": "slow travel",
            },
            "stops": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of cities/stops included in the trip.",
            },
        },
        "required": ["destination", "days"],
    }

    async def execute(
        self,
        destination: str,
        days: int = 5,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        budget: str = "moderate",
        traveler_count: int = 1,
        travel_style: str = "slow travel",
        interests: Optional[List[str]] = None,
        stops: Optional[List[str]] = None,
        **kwargs,
    ) -> ToolResult:
        from backend.app.travel.schemas.itinerary_engine import ItineraryEngineInput
        from backend.app.travel.services.itinerary_engine import itinerary_engine

        engine_input = ItineraryEngineInput(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            duration_days=days,
            budget=budget,
            traveler_count=traveler_count,
            interests=interests or [],
            travel_style=travel_style,
        )

        structured_trip = await itinerary_engine.generate(engine_input)
        data = structured_trip.to_dict()

        # Ensure compatibility with both flat and detailed day representations
        for day in data["days"]:
            day["location"] = day.get("neighborhood_cluster", destination)
            m_acts = day.get("morning", {}).get("activities", [])
            a_acts = day.get("afternoon", {}).get("activities", [])
            e_acts = day.get("evening", {}).get("activities", [])
            day["morning_desc"] = m_acts[0]["description"] if m_acts else "Morning exploration."
            day["afternoon_desc"] = a_acts[0]["description"] if a_acts else "Afternoon cultural immersion."
            day["evening_desc"] = e_acts[0]["description"] if e_acts else "Sunset relaxation."

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=data,
            message=f"Created {structured_trip.duration_days}-day itinerary for {destination}.",
            provenance=DataProvenance.CALCULATED,
            is_live_data=False,
            metadata={"destination": destination, "days": structured_trip.duration_days},
        )


class SaveTripTool(BaseTool):
    """Tool to save a generated trip or itinerary into the database."""

    name = "save_trip"
    description = (
        "Save a trip or itinerary structure into the KHOJAI database for future retrieval, sharing, or modification."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Title of the trip (e.g. '5-Day Rajasthan Heritage Circuit').",
            },
            "summary": {
                "type": "string",
                "description": "Summary or description of the journey.",
            },
            "total_budget": {
                "type": "string",
                "description": "Estimated budget string (e.g. '₹25,000 / person').",
            },
            "user_id": {
                "type": "string",
                "description": "Optional UUID of the owning user.",
            },
            "days": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Day-by-day plan items.",
            },
        },
        "required": ["title", "summary"],
    }

    async def execute(
        self,
        title: str,
        summary: str,
        total_budget: str = "₹15,000 / person",
        user_id: Optional[str] = None,
        days: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ToolResult:
        share_token = f"trip-{uuid.uuid4().hex[:8]}"
        uid = None
        if user_id:
            try:
                uid = uuid.UUID(user_id)
            except ValueError:
                pass

        async with async_session_factory() as session:
            itinerary = Itinerary(
                user_id=uid,
                share_token=share_token,
                title=title,
                subtitle=f"{len(days or [])} days · Curated Journey",
                summary=summary,
                total_budget=total_budget,
                preferences={"days": len(days or [])},
            )
            session.add(itinerary)
            await session.flush()

            if days:
                for idx, day_data in enumerate(days, start=1):
                    m = day_data.get("morning_desc") or (day_data.get("morning", {}).get("theme", "") if isinstance(day_data.get("morning"), dict) else str(day_data.get("morning", "")))
                    a = day_data.get("afternoon_desc") or (day_data.get("afternoon", {}).get("theme", "") if isinstance(day_data.get("afternoon"), dict) else str(day_data.get("afternoon", "")))
                    e = day_data.get("evening_desc") or (day_data.get("evening", {}).get("theme", "") if isinstance(day_data.get("evening"), dict) else str(day_data.get("evening", "")))
                    body_text = f"{m} {a} {e}".strip() or f"Curated itinerary activities for Day {idx}."

                    day_item = ItineraryDay(
                        itinerary_id=itinerary.id,
                        day_number=f"{idx:02d}",
                        place_name=day_data.get("location", "Curated Stop"),
                        title=day_data.get("title", f"Day {idx}"),
                        body=body_text,
                        accent_color="#5d6b43",
                        sort_order=idx,
                    )
                    session.add(day_item)

            await session.commit()
            await session.refresh(itinerary)

            result_data = {
                "id": str(itinerary.id),
                "share_token": itinerary.share_token,
                "title": itinerary.title,
                "total_budget": itinerary.total_budget,
                "days_count": len(days or []),
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=result_data,
                message=f"Trip successfully saved with ID '{itinerary.id}' and share token '{itinerary.share_token}'.",
                provenance=DataProvenance.SYSTEM_STATE,
                is_live_data=True,
                metadata={"itinerary_id": str(itinerary.id), "share_token": share_token},
            )


class RetrieveTripTool(BaseTool):
    """Tool to retrieve a saved trip from the database."""

    name = "retrieve_trip"
    description = (
        "Retrieve a saved trip or itinerary from the database by ID or share token."
    )
    parameters = {
        "type": "object",
        "properties": {
            "trip_identifier": {
                "type": "string",
                "description": "Trip UUID or share token (e.g. 'trip-a1b2c3d4').",
            },
        },
        "required": ["trip_identifier"],
    }

    async def execute(self, trip_identifier: str, **kwargs) -> ToolResult:
        async with async_session_factory() as session:
            stmt = select(Itinerary).where(
                (Itinerary.share_token == trip_identifier)
            )
            # Try UUID matching if possible
            try:
                uid = uuid.UUID(trip_identifier)
                stmt = select(Itinerary).where((Itinerary.id == uid) | (Itinerary.share_token == trip_identifier))
            except ValueError:
                pass

            res = await session.execute(stmt)
            itinerary = res.scalar_one_or_none()

            if not itinerary:
                return ToolResult(
                    tool_name=self.name,
                    success=False,
                    data=None,
                    message=f"No saved trip found with identifier '{trip_identifier}'.",
                    provenance=DataProvenance.LOCAL_DATABASE,
                    is_live_data=False,
                )

            # Load days
            days_stmt = select(ItineraryDay).where(ItineraryDay.itinerary_id == itinerary.id).order_by(ItineraryDay.sort_order.asc())
            days_res = await session.execute(days_stmt)
            days = days_res.scalars().all()

            data = {
                "id": str(itinerary.id),
                "share_token": itinerary.share_token,
                "title": itinerary.title,
                "subtitle": itinerary.subtitle,
                "summary": itinerary.summary,
                "total_budget": itinerary.total_budget,
                "days": [
                    {
                        "day_number": d.day_number,
                        "place_name": d.place_name,
                        "title": d.title,
                        "body": d.body,
                    }
                    for d in days
                ],
            }

            return ToolResult(
                tool_name=self.name,
                success=True,
                data=data,
                message=f"Retrieved trip '{itinerary.title}'.",
                provenance=DataProvenance.LOCAL_DATABASE,
                is_live_data=True,
                metadata={"id": str(itinerary.id)},
            )
