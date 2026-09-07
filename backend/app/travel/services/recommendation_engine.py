"""Personalized Travel Recommendation & Scoring Engine for KHOJAI.

Calculates explainable, multi-factor recommendation scores for Destinations,
Hotels, Activities, Restaurants, and Itineraries based on UserTravelPreference.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.destination import Destination
from backend.app.travel.models.poi import Activity, Attraction, Hotel, Restaurant
from backend.app.travel.models.trip import Trip, UserTravelPreference
from backend.app.travel.schemas.trip import UserTravelPreferenceOut


class MatchBreakdown(BaseModel):
    """Detailed score breakdown across all 6 recommendation dimensions (0.0 to 1.0)."""

    destination_match: float = Field(..., ge=0.0, le=1.0)
    interest_match: float = Field(..., ge=0.0, le=1.0)
    budget_match: float = Field(..., ge=0.0, le=1.0)
    activity_match: float = Field(..., ge=0.0, le=1.0)
    travel_style_match: float = Field(..., ge=0.0, le=1.0)
    historical_preference: float = Field(..., ge=0.0, le=1.0)


class ScoredRecommendation(BaseModel):
    """Explainable scored travel recommendation."""

    entity_type: str = Field(..., description="'destination', 'hotel', 'activity', 'restaurant', 'itinerary'")
    entity_id: str = Field(..., description="UUID or unique identifier of the entity")
    title: str = Field(..., description="Display title or name of the entity")
    score: float = Field(..., ge=0.0, le=100.0, description="Composite recommendation score from 0 to 100")
    match_breakdown: MatchBreakdown = Field(..., description="Itemized scores for all 6 dimensions")
    explanation: str = Field(..., description="Transparent, human-readable reason for recommendation")
    details: Dict[str, Any] = Field(default_factory=dict, description="Entity attributes (price, location, rating, tags)")


class PersonalizedRecommendationEngine:
    """Deterministic, explainable recommendation scoring engine."""

    # Normalization helper for budget tiers
    BUDGET_MAP = {
        "budget": "₹",
        "low": "₹",
        "moderate": "₹₹",
        "mid": "₹₹",
        "medium": "₹₹",
        "luxury": "₹₹₹",
        "high": "₹₹₹",
    }

    @classmethod
    def normalize_budget(cls, raw_budget: Optional[str]) -> str:
        """Map text budget descriptors to standardized currency tiers."""
        if not raw_budget:
            return "₹₹"
        clean = raw_budget.strip().lower()
        if "₹₹₹" in clean or "luxury" in clean:
            return "₹₹₹"
        if "₹₹" in clean or "moderate" in clean or "mid" in clean:
            return "₹₹"
        if "₹" in clean or "budget" in clean or "backpack" in clean:
            return "₹"
        return "₹₹"

    @classmethod
    def compute_composite_score(cls, breakdown: MatchBreakdown) -> float:
        """Compute composite score using geometric product normalized to [0, 100].

        score = (destination_match * interest_match * budget_match *
                 activity_match * travel_style_match * historical_preference) ** (1/6) * 100
        """
        product = (
            max(0.10, breakdown.destination_match)
            * max(0.10, breakdown.interest_match)
            * max(0.10, breakdown.budget_match)
            * max(0.10, breakdown.activity_match)
            * max(0.10, breakdown.travel_style_match)
            * max(0.10, breakdown.historical_preference)
        )
        geometric_mean = math.pow(product, 1.0 / 6.0)
        return round(geometric_mean * 100.0, 1)

    # -------------------------------------------------------------------------
    # Destination Scoring
    # -------------------------------------------------------------------------

    @classmethod
    def score_destination(
        cls,
        dest: Destination,
        pref: UserTravelPreference | UserTravelPreferenceOut,
    ) -> ScoredRecommendation:
        """Score a Destination against user travel preferences."""
        # 1. Destination match
        dest_match = 0.50
        pref_dests = [d.lower() for d in (pref.preferred_destinations or [])]
        pref_regions = [r.lower() for r in getattr(pref, "preferred_regions", []) or []]
        name_lower = dest.name.lower()
        state_lower = dest.state.lower()
        region_lower = dest.region.lower()

        if any(d in name_lower or name_lower in d for d in pref_dests):
            dest_match = 1.00
        elif any(d in state_lower for d in pref_dests) or any(r in region_lower for r in pref_regions):
            dest_match = 0.85
        elif getattr(dest, "trust_score", 0) >= 85:
            dest_match = 0.70

        # 2. Interest match
        user_interests = [i.lower() for i in (pref.interests or [])]
        matched_interests = []
        dest_text = f"{dest.category} {dest.description}".lower()
        for interest in user_interests:
            if interest in dest_text:
                matched_interests.append(interest.capitalize())

        if user_interests:
            interest_match = min(1.0, 0.35 + 0.65 * (len(matched_interests) / max(1, len(user_interests))))
        else:
            interest_match = 0.75

        # 3. Budget match
        pref_tier = cls.normalize_budget(pref.budget_range or getattr(pref, "budget_preference", "₹₹"))
        dest_tier = cls.normalize_budget(dest.budget)
        tier_weights = {"₹": 1, "₹₹": 2, "₹₹₹": 3}
        diff = abs(tier_weights.get(pref_tier, 2) - tier_weights.get(dest_tier, 2))
        budget_match = 1.00 if diff == 0 else (0.65 if diff == 1 else 0.35)

        # 4. Activity match
        pref_acts = [a.lower() for a in (pref.preferred_activities or [])]
        matched_activities = [a for a in pref_acts if a in dest_text]
        activity_match = min(1.0, 0.40 + 0.60 * (len(matched_activities) / max(1, len(pref_acts)))) if pref_acts else 0.70

        # 5. Travel style match
        style = (pref.travel_style or "Balanced").lower()
        travel_style_match = 0.55
        if style in dest_text or ("cultur" in style and "culture" in dest_text):
            travel_style_match = 0.95
        elif "slow" in style and ("village" in dest_text or "island" in dest_text or "nature" in dest_text):
            travel_style_match = 0.90
        elif "adventure" in style and ("trek" in dest_text or "altitude" in dest_text or "valley" in dest_text):
            travel_style_match = 0.92

        # 6. Historical preference
        trust_norm = min(1.0, max(0.5, (getattr(dest, "trust_score", 85) / 100.0)))
        historical_preference = trust_norm

        breakdown = MatchBreakdown(
            destination_match=round(dest_match, 2),
            interest_match=round(interest_match, 2),
            budget_match=round(budget_match, 2),
            activity_match=round(activity_match, 2),
            travel_style_match=round(travel_style_match, 2),
            historical_preference=round(historical_preference, 2),
        )
        score = cls.compute_composite_score(breakdown)

        # Generate explanation
        explanation_parts = []
        if matched_interests:
            explanation_parts.append(f"matches your interest in {', '.join(matched_interests[:2])}")
        if budget_match >= 0.8:
            explanation_parts.append(f"fits your selected {pref.budget_range or 'moderate'} budget")
        if dest_match >= 0.85:
            explanation_parts.append(f"aligns with your preferred region in {dest.region}")
        if travel_style_match >= 0.85:
            explanation_parts.append(f"fits your {pref.travel_style} travel style")

        if not explanation_parts:
            explanation_parts.append(f"features verified cultural trails in {dest.state}")

        explanation = f"Recommended because it {', '.join(explanation_parts)}."

        return ScoredRecommendation(
            entity_type="destination",
            entity_id=str(dest.id),
            title=dest.name,
            score=score,
            match_breakdown=breakdown,
            explanation=explanation,
            details={
                "state": dest.state,
                "region": dest.region,
                "category": dest.category,
                "budget_tier": dest.budget,
                "best_season": dest.best_season,
                "trust_score": dest.trust_score,
            },
        )

    # -------------------------------------------------------------------------
    # Hotel Scoring
    # -------------------------------------------------------------------------

    @classmethod
    def score_hotel(
        cls,
        hotel: Hotel,
        pref: UserTravelPreference | UserTravelPreferenceOut,
        target_destination: Optional[str] = None,
    ) -> ScoredRecommendation:
        """Score an accommodation against user travel preferences."""
        # 1. Destination match
        dest_match = 0.90 if target_destination else 0.70

        # 2. Interest match
        user_interests = [i.lower() for i in (pref.interests or [])]
        stay_text = f"{hotel.name} {hotel.stay_type} {hotel.address}".lower()
        interest_hits = [i for i in user_interests if i in stay_text or ("heritage" in i and "heritage" in stay_text)]
        interest_match = 0.85 if interest_hits else 0.65

        # 3. Budget match
        pref_tier = cls.normalize_budget(pref.budget_range or getattr(pref, "budget_preference", "₹₹"))
        hotel_tier = cls.normalize_budget(hotel.price_level)
        tier_weights = {"₹": 1, "₹₹": 2, "₹₹₹": 3}
        diff = abs(tier_weights.get(pref_tier, 2) - tier_weights.get(hotel_tier, 2))
        budget_match = 1.00 if diff == 0 else (0.60 if diff == 1 else 0.30)

        # 4. Activity match (proximity to serene/local living)
        activity_match = 0.75

        # 5. Travel style / Accommodation match
        pref_stays = [s.lower() for s in (pref.preferred_accommodation or getattr(pref, "preferred_stay_types", []) or [])]
        stay_lower = hotel.stay_type.lower()
        if any(s in stay_lower or stay_lower in s for s in pref_stays):
            travel_style_match = 0.95
        elif "slow" in (pref.travel_style or "").lower() and ("homestay" in stay_lower or "eco" in stay_lower):
            travel_style_match = 0.90
        else:
            travel_style_match = 0.60

        # 6. Historical preference (Rating)
        rating = hotel.rating or 4.5
        historical_preference = min(1.0, max(0.5, rating / 5.0))

        breakdown = MatchBreakdown(
            destination_match=round(dest_match, 2),
            interest_match=round(interest_match, 2),
            budget_match=round(budget_match, 2),
            activity_match=round(activity_match, 2),
            travel_style_match=round(travel_style_match, 2),
            historical_preference=round(historical_preference, 2),
        )
        score = cls.compute_composite_score(breakdown)

        explanation_parts = []
        if travel_style_match >= 0.85:
            explanation_parts.append(f"offers your preferred {hotel.stay_type} accommodation")
        if budget_match >= 0.80:
            explanation_parts.append(f"fits your {pref.budget_range or 'moderate'} budget tier")
        if rating >= 4.5:
            explanation_parts.append(f"has high traveler community ratings ({rating}★)")

        explanation = f"Recommended because it {', '.join(explanation_parts)}."

        return ScoredRecommendation(
            entity_type="hotel",
            entity_id=str(hotel.id),
            title=hotel.name,
            score=score,
            match_breakdown=breakdown,
            explanation=explanation,
            details={
                "stay_type": hotel.stay_type,
                "address": hotel.address,
                "price_level": hotel.price_level,
                "price_per_night": hotel.price_per_night,
                "rating": hotel.rating,
            },
        )

    # -------------------------------------------------------------------------
    # Activity Scoring
    # -------------------------------------------------------------------------

    @classmethod
    def score_activity(
        cls,
        act: Activity,
        pref: UserTravelPreference | UserTravelPreferenceOut,
    ) -> ScoredRecommendation:
        """Score an experiential activity against user travel preferences."""
        dest_match = 0.85
        pref_dests = [d.lower() for d in (pref.preferred_destinations or [])]
        act_text = f"{act.title} {act.activity_type} {act.description}".lower()
        if any(d in act_text for d in pref_dests):
            dest_match = 0.95

        # 2. Interest match
        user_interests = [i.lower() for i in (pref.interests or [])]
        matched_interests = []
        for i in user_interests:
            stem = i.rstrip("s")
            if i in act_text or (len(stem) >= 3 and stem in act_text):
                matched_interests.append(i.capitalize())

        interest_match = min(1.0, 0.40 + 0.60 * (len(matched_interests) / max(1, len(user_interests)))) if user_interests else 0.80

        # 3. Budget match
        budget_match = 0.90  # Activities generally moderate in experiential travel

        # 4. Activity match
        pref_acts = [a.lower() for a in (pref.preferred_activities or [])]
        act_type_lower = act.activity_type.lower()
        if any(p in act_type_lower or act_type_lower in p or p in act_text for p in pref_acts):
            activity_match = 0.95
        else:
            activity_match = 0.65

        # 5. Travel style match
        style = (pref.travel_style or "").lower()
        if "culture" in style and ("workshop" in act_text or "cultural" in act_text or "village" in act_text):
            travel_style_match = 0.95
        elif "adventure" in style and ("trek" in act_text or "climb" in act_text or "river" in act_text):
            travel_style_match = 0.95
        elif "slow" in style and ("walk" in act_text or "workshop" in act_text or "bird" in act_text):
            travel_style_match = 0.90
        else:
            travel_style_match = 0.70

        # 6. Historical preference
        historical_preference = 0.85


        breakdown = MatchBreakdown(
            destination_match=round(dest_match, 2),
            interest_match=round(interest_match, 2),
            budget_match=round(budget_match, 2),
            activity_match=round(activity_match, 2),
            travel_style_match=round(travel_style_match, 2),
            historical_preference=round(historical_preference, 2),
        )
        score = cls.compute_composite_score(breakdown)

        explanation_parts = []
        if activity_match >= 0.85:
            explanation_parts.append(f"matches your preferred activity in {act.activity_type}")
        if matched_interests:
            explanation_parts.append(f"engages your interest in {', '.join(matched_interests[:2])}")
        if travel_style_match >= 0.85:
            explanation_parts.append(f"aligns with your {pref.travel_style} travel style")

        if not explanation_parts:
            explanation_parts.append(f"offers immersive local exploration")

        explanation = f"Recommended because it {', '.join(explanation_parts)}."

        return ScoredRecommendation(
            entity_type="activity",
            entity_id=str(act.id),
            title=act.title,
            score=score,
            match_breakdown=breakdown,
            explanation=explanation,
            details={
                "activity_type": act.activity_type,
                "duration_hours": act.duration_hours,
                "price_range": act.price_range,
                "guide_required": act.guide_required,
            },
        )

    # -------------------------------------------------------------------------
    # Restaurant Scoring
    # -------------------------------------------------------------------------

    @classmethod
    def score_restaurant(
        cls,
        rest: Restaurant,
        pref: UserTravelPreference | UserTravelPreferenceOut,
    ) -> ScoredRecommendation:
        """Score a dining place against user food and dietary preferences."""
        dest_match = 0.85

        # 2. Interest match (culinary/food interests)
        user_interests = [i.lower() for i in (pref.interests or [])]
        interest_match = 0.90 if any("food" in i or "culinary" in i or "culture" in i for i in user_interests) else 0.70

        # 3. Budget match
        pref_tier = cls.normalize_budget(pref.budget_range or getattr(pref, "budget_preference", "₹₹"))
        rest_tier = cls.normalize_budget(rest.price_range)
        tier_weights = {"₹": 1, "₹₹": 2, "₹₹₹": 3}
        diff = abs(tier_weights.get(pref_tier, 2) - tier_weights.get(rest_tier, 2))
        budget_match = 1.00 if diff == 0 else (0.65 if diff == 1 else 0.40)

        # 4. Activity match
        activity_match = 0.75

        # 5. Food / Dietary preferences match
        food_prefs = [f.lower() for f in (pref.food_preferences or [])]
        diet_need = getattr(pref, "dietary_needs", "none").lower()
        rest_text = f"{rest.cuisine_type} {' '.join(rest.must_try_dishes or [])}".lower()

        travel_style_match = 0.60
        matched_foods = []
        for fp in food_prefs:
            if fp in rest_text or ("veg" in fp and "vegetarian" in rest_text):
                matched_foods.append(fp.capitalize())

        if "strictly_vegetarian" in diet_need or "vegetarian" in diet_need or "jain" in diet_need:
            if "pure vegetarian" in rest_text or "vegetarian" in rest_text:
                travel_style_match = 1.00
                matched_foods.append("Vegetarian")
            else:
                travel_style_match = 0.30
        elif matched_foods:
            travel_style_match = 0.95
        else:
            travel_style_match = 0.75

        # 6. Historical preference (Rating)
        rating = rest.rating or 4.5
        historical_preference = min(1.0, max(0.5, rating / 5.0))

        breakdown = MatchBreakdown(
            destination_match=round(dest_match, 2),
            interest_match=round(interest_match, 2),
            budget_match=round(budget_match, 2),
            activity_match=round(activity_match, 2),
            travel_style_match=round(travel_style_match, 2),
            historical_preference=round(historical_preference, 2),
        )
        score = cls.compute_composite_score(breakdown)

        explanation_parts = []
        if matched_foods:
            explanation_parts.append(f"offers dishes matching your {', '.join(matched_foods[:2])} preferences")
        elif "vegetarian" in rest_text and any("veg" in f for f in food_prefs):
            explanation_parts.append("serves vegetarian-friendly regional specialties")
        if budget_match >= 0.80:
            explanation_parts.append(f"fits your dining budget")
        if rating >= 4.4:
            explanation_parts.append(f"is highly rated ({rating}★) for authentic local flavors")

        explanation = f"Recommended because it {', '.join(explanation_parts)}."

        return ScoredRecommendation(
            entity_type="restaurant",
            entity_id=str(rest.id),
            title=rest.name,
            score=score,
            match_breakdown=breakdown,
            explanation=explanation,
            details={
                "cuisine_type": rest.cuisine_type,
                "price_range": rest.price_range,
                "rating": rest.rating,
                "must_try_dishes": rest.must_try_dishes,
            },
        )

    # -------------------------------------------------------------------------
    # Itinerary / Trip Scoring
    # -------------------------------------------------------------------------

    @classmethod
    def score_itinerary(
        cls,
        trip: Trip,
        pref: UserTravelPreference | UserTravelPreferenceOut,
    ) -> ScoredRecommendation:
        """Score a Trip / Itinerary against user travel preferences."""
        # 1. Destination match
        dest_match = 0.80
        pref_dests = [d.lower() for d in (pref.preferred_destinations or [])]
        if any(d in trip.title.lower() for d in pref_dests):
            dest_match = 1.00

        # 2. Interest match
        user_interests = [i.lower() for i in (pref.interests or [])]
        trip_text = f"{trip.title} {trip.notes or ''}".lower()
        matched_interests = [i.capitalize() for i in user_interests if i in trip_text]
        interest_match = 0.90 if matched_interests else 0.70

        # 3. Budget match
        pref_tier = cls.normalize_budget(pref.budget_range or getattr(pref, "budget_preference", "₹₹"))
        trip_tier = cls.normalize_budget(getattr(trip, "budget_tier", "₹₹"))
        budget_match = 1.00 if pref_tier == trip_tier else 0.65

        # 4. Activity match
        activity_match = 0.80

        # 5. Travel style & Duration match
        target_days = pref.preferred_trip_duration or 5
        trip_days = len(trip.days) if getattr(trip, "days", None) else 5
        day_diff = abs(target_days - trip_days)
        duration_factor = 1.00 if day_diff == 0 else max(0.50, 1.0 - (day_diff * 0.15))
        travel_style_match = round(duration_factor, 2)

        # 6. Historical preference
        historical_preference = 0.85

        breakdown = MatchBreakdown(
            destination_match=round(dest_match, 2),
            interest_match=round(interest_match, 2),
            budget_match=round(budget_match, 2),
            activity_match=round(activity_match, 2),
            travel_style_match=round(travel_style_match, 2),
            historical_preference=round(historical_preference, 2),
        )
        score = cls.compute_composite_score(breakdown)

        explanation_parts = []
        if day_diff <= 1:
            explanation_parts.append(f"matches your ideal {target_days}-day trip duration")
        if matched_interests:
            explanation_parts.append(f"covers your interests in {', '.join(matched_interests[:2])}")
        if budget_match >= 0.8:
            explanation_parts.append(f"fits your {pref.budget_range or 'moderate'} budget")

        explanation = f"Recommended because it {', '.join(explanation_parts)}."

        return ScoredRecommendation(
            entity_type="itinerary",
            entity_id=str(trip.id),
            title=trip.title,
            score=score,
            match_breakdown=breakdown,
            explanation=explanation,
            details={
                "days_count": len(trip.days) if getattr(trip, "days", None) else 0,
                "status": trip.status,
                "notes": trip.notes,
            },
        )

    # -------------------------------------------------------------------------
    # Batch Recommendation Service
    # -------------------------------------------------------------------------

    @classmethod
    async def get_personalized_recommendations(
        cls,
        session: AsyncSession,
        user_id: UUID,
        category: str = "all",
        destination_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[ScoredRecommendation]:
        """Fetch and score candidates across destinations, hotels, activities, restaurants, and itineraries."""
        # 1. Fetch user preferences
        stmt = select(UserTravelPreference).where(UserTravelPreference.user_id == user_id)
        result = await session.execute(stmt)
        pref = result.scalars().first()
        if not pref:
            # Fallback default preferences
            pref = UserTravelPreference(
                user_id=user_id,
                preferred_destinations=[],
                interests=["Culture", "Nature", "Heritage"],
                travel_style="Cultural",
                budget_range="moderate",
                preferred_accommodation=["Homestay", "Heritage Haveli"],
                preferred_activities=["Sightseeing", "Cultural Workshop"],
                food_preferences=["Local Traditional"],
                transportation_preferences=["Train", "Flight"],
                preferred_trip_duration=5,
            )

        recommendations: List[ScoredRecommendation] = []

        # 2. Destinations
        if category in ("all", "destinations", "destination"):
            dest_stmt = select(Destination).limit(limit * 2)
            dest_res = await session.execute(dest_stmt)
            dests = dest_res.scalars().all()
            for d in dests:
                rec = cls.score_destination(d, pref)
                recommendations.append(rec)

        # 3. Hotels
        if category in ("all", "hotels", "hotel"):
            hotel_stmt = select(Hotel)
            if destination_name:
                hotel_stmt = hotel_stmt.join(Destination).where(Destination.name.ilike(f"%{destination_name}%"))
            hotel_stmt = hotel_stmt.limit(limit * 2)
            hotel_res = await session.execute(hotel_stmt)
            hotels = hotel_res.scalars().all()
            for h in hotels:
                rec = cls.score_hotel(h, pref, target_destination=destination_name)
                recommendations.append(rec)

        # 4. Activities
        if category in ("all", "activities", "activity"):
            act_stmt = select(Activity)
            if destination_name:
                act_stmt = act_stmt.join(Destination).where(Destination.name.ilike(f"%{destination_name}%"))
            act_stmt = act_stmt.limit(limit * 2)
            act_res = await session.execute(act_stmt)
            acts = act_res.scalars().all()
            for a in acts:
                rec = cls.score_activity(a, pref)
                recommendations.append(rec)

        # 5. Restaurants
        if category in ("all", "restaurants", "restaurant"):
            rest_stmt = select(Restaurant)
            if destination_name:
                rest_stmt = rest_stmt.join(Destination).where(Destination.name.ilike(f"%{destination_name}%"))
            rest_stmt = rest_stmt.limit(limit * 2)
            rest_res = await session.execute(rest_stmt)
            rests = rest_res.scalars().all()
            for r in rests:
                rec = cls.score_restaurant(r, pref)
                recommendations.append(rec)

        # 6. Itineraries
        if category in ("all", "itineraries", "itinerary"):
            trip_stmt = select(Trip).where(Trip.user_id == user_id).limit(limit)
            trip_res = await session.execute(trip_stmt)
            trips = trip_res.scalars().all()
            for t in trips:
                rec = cls.score_itinerary(t, pref)
                recommendations.append(rec)

        # Sort by composite score descending
        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:limit]


recommendation_engine = PersonalizedRecommendationEngine()
