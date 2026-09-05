"""Trip planning service for custom itineraries, preference matching, and draft compilation."""

from datetime import date, timedelta
from typing import List, Optional, Sequence
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.travel.models.trip import Trip, TripDay, TripItem, UserTravelPreference
from backend.app.travel.repositories.destination_repo import DestinationRepository
from backend.app.travel.repositories.trip_repo import TripRepository
from backend.app.travel.schemas.trip import (
    TripCreate,
    TripOut,
    UserTravelPreferenceCreate,
    UserTravelPreferenceOut,
    UserTravelPreferenceUpdate,
)


class TripService:
    """Service handling multi-day trip compilation, sharing, and travel preference management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.trip_repo = TripRepository(session)
        self.dest_repo = DestinationRepository(session)

    async def get_trip(self, trip_id: UUID) -> Optional[TripOut]:
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            return None
        return TripOut.model_validate(trip)

    async def get_by_share_token(self, share_token: str) -> Optional[TripOut]:
        trip = await self.trip_repo.get_by_share_token(share_token)
        if not trip:
            return None
        return TripOut.model_validate(trip)

    async def list_user_trips(self, user_id: UUID, limit: int = 50, offset: int = 0) -> Sequence[Trip]:
        return await self.trip_repo.list_by_user(user_id=user_id, limit=limit, offset=offset)

    async def create_trip(self, data: TripCreate, user_id: Optional[UUID] = None) -> TripOut:
        """Create a complete trip with days and scheduled items."""
        effective_user_id = user_id or data.user_id
        trip = await self.trip_repo.create_trip(
            title=data.title,
            user_id=effective_user_id,
            destination_id=data.destination_id,
            description=data.description,
            start_date=data.start_date,
            end_date=data.end_date,
            total_days=data.total_days,
            budget_tier=data.budget_tier,
            status=data.status,
            is_public=data.is_public,
        )

        # Create structured days and items
        for day_in in (data.days or []):
            day = await self.trip_repo.add_day(
                trip_id=trip.id,
                day_number=day_in.day_number,
                day_date=day_in.day_date,
                theme_title=day_in.theme_title,
                notes=day_in.notes,
            )
            for idx, item_in in enumerate(day_in.items or [], start=1):
                await self.trip_repo.add_item(
                    trip_day_id=day.id,
                    item_type=item_in.item_type,
                    title=item_in.title,
                    description=item_in.description,
                    start_time=item_in.start_time,
                    end_time=item_in.end_time,
                    estimated_cost=item_in.estimated_cost,
                    sort_order=item_in.sort_order or idx,
                    attraction_id=item_in.attraction_id,
                    hotel_id=item_in.hotel_id,
                    restaurant_id=item_in.restaurant_id,
                    activity_id=item_in.activity_id,
                )

        # Refresh eager loaded trip
        loaded_trip = await self.trip_repo.get_by_id(trip.id)
        return TripOut.model_validate(loaded_trip)

    async def generate_draft_itinerary(
        self,
        destination_slug: str,
        total_days: int = 4,
        start_date: Optional[date] = None,
        user_id: Optional[UUID] = None,
    ) -> TripOut:
        """Intelligently assemble an automated travel draft from curated local POIs."""
        dest = await self.dest_repo.get_by_slug(destination_slug)
        if not dest:
            raise ValueError(f"Destination '{destination_slug}' not found")

        attractions = list(getattr(dest, "attractions", []))
        activities = list(getattr(dest, "activities", []))
        hotels = list(getattr(dest, "hotels", []))
        restaurants = list(getattr(dest, "restaurants", []))

        trip_title = f"{dest.name} Discovery & Cultural Immersion"
        description = f"A {total_days}-day thoughtfully curated journey exploring the heritage, trails, and life of {dest.name}."

        trip = await self.trip_repo.create_trip(
            title=trip_title,
            user_id=user_id,
            destination_id=dest.id,
            description=description,
            start_date=start_date,
            end_date=(start_date + timedelta(days=total_days - 1)) if start_date else None,
            total_days=total_days,
            budget_tier=dest.budget or "₹₹",
            status="draft",
            is_public=False,
        )

        # Primary stay
        primary_hotel = hotels[0] if hotels else None

        for day_idx in range(1, total_days + 1):
            day_date = (start_date + timedelta(days=day_idx - 1)) if start_date else None
            theme = f"Day {day_idx}: Sights and Local Living in {dest.name}"
            if day_idx == 1:
                theme = f"Arrival, Check-in & Settle in {dest.name}"
            elif day_idx == total_days:
                theme = f"Morning Trails, Local Handicrafts & Farewell to {dest.name}"

            day = await self.trip_repo.add_day(
                trip_id=trip.id,
                day_number=day_idx,
                day_date=day_date,
                theme_title=theme,
                notes="Wear comfortable walking shoes; carry local cash and photo ID.",
            )

            sort = 1
            # Morning check-in or start
            if primary_hotel and day_idx == 1:
                await self.trip_repo.add_item(
                    trip_day_id=day.id,
                    item_type="hotel",
                    title=f"Check into {primary_hotel.name}",
                    description=f"Settle into {primary_hotel.stay_type} at {primary_hotel.address}",
                    start_time="11:00 AM",
                    end_time="12:30 PM",
                    sort_order=sort,
                    hotel_id=primary_hotel.id,
                )
                sort += 1

            # Attraction
            attr_idx = (day_idx - 1) % max(len(attractions), 1)
            if attractions:
                cur_attr = attractions[attr_idx]
                await self.trip_repo.add_item(
                    trip_day_id=day.id,
                    item_type="attraction",
                    title=cur_attr.name,
                    description=cur_attr.description[:180] + "...",
                    start_time="02:00 PM",
                    end_time="04:30 PM",
                    sort_order=sort,
                    attraction_id=cur_attr.id,
                )
                sort += 1

            # Activity
            act_idx = (day_idx - 1) % max(len(activities), 1)
            if activities:
                cur_act = activities[act_idx]
                await self.trip_repo.add_item(
                    trip_day_id=day.id,
                    item_type="activity",
                    title=cur_act.title,
                    description=cur_act.description[:180] + "...",
                    start_time="05:00 PM",
                    end_time="06:30 PM",
                    estimated_cost=cur_act.price_range,
                    sort_order=sort,
                    activity_id=cur_act.id,
                )
                sort += 1

            # Dinner
            rest_idx = (day_idx - 1) % max(len(restaurants), 1)
            if restaurants:
                cur_rest = restaurants[rest_idx]
                dishes = ", ".join(cur_rest.must_try_dishes[:2]) if cur_rest.must_try_dishes else "local meal"
                await self.trip_repo.add_item(
                    trip_day_id=day.id,
                    item_type="restaurant",
                    title=f"Dinner at {cur_rest.name}",
                    description=f"Traditional {cur_rest.cuisine_type} dining. Recommended: {dishes}.",
                    start_time="07:30 PM",
                    end_time="09:00 PM",
                    sort_order=sort,
                    restaurant_id=cur_rest.id,
                )

        loaded_trip = await self.trip_repo.get_by_id(trip.id)
        return TripOut.model_validate(loaded_trip)

    async def get_or_create_user_preferences(self, user_id: UUID) -> UserTravelPreferenceOut:
        pref = await self.trip_repo.get_user_preference(user_id)
        if not pref:
            pref = await self.trip_repo.upsert_user_preference(
                user_id=user_id,
                budget_preference="₹₹",
                preferred_pace="balanced",
                travel_styles=["Slow travel", "Culture-led"],
                dietary_needs="none",
                fitness_level="moderate",
                preferred_stay_types=["Homestay", "Eco-Lodge"],
                preferred_regions=["Himalayas", "Northeast"],
            )
        return UserTravelPreferenceOut.model_validate(pref)

    async def update_user_preferences(self, user_id: UUID, data: UserTravelPreferenceUpdate) -> UserTravelPreferenceOut:
        update_kwargs = data.model_dump(exclude_unset=True)
        pref = await self.trip_repo.upsert_user_preference(user_id=user_id, **update_kwargs)
        return UserTravelPreferenceOut.model_validate(pref)
