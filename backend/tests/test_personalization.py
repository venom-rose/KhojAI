"""Tests for KHOJAI Personalized Travel Recommendations, UserTravelPreference, and Scoring Engine."""

import math
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.destination import Destination
from backend.app.models.user import User
from backend.app.travel.models.poi import Activity, Attraction, Hotel, Restaurant
from backend.app.travel.models.trip import Trip, UserTravelPreference
from backend.app.travel.schemas.trip import (
    UserTravelPreferenceCreate,
    UserTravelPreferenceOut,
    UserTravelPreferenceUpdate,
)
from backend.app.travel.services.recommendation_engine import (
    MatchBreakdown,
    PersonalizedRecommendationEngine,
    recommendation_engine,
)
from backend.app.ai.tools.trip_tools import GetUserPreferencesTool, GetPersonalizedRecommendationsTool


@pytest.mark.asyncio
async def test_user_travel_preference_model_and_schemas(db_session: AsyncSession):
    """Test UserTravelPreference model creation, all 9 fields, and schema conversions."""
    user = User(
        email="personal.pref@khojai.in",
        hashed_password="hashed_password",
        role="traveler",
        full_name="Personal Traveler",
    )
    db_session.add(user)
    await db_session.flush()

    pref = UserTravelPreference(
        user_id=user.id,
        preferred_destinations=["Jaipur", "Ziro"],
        interests=["History", "Heritage", "Architecture"],
        travel_style="Cultural",
        budget_range="moderate",
        preferred_accommodation=["Heritage Haveli", "Homestay"],
        preferred_activities=["Sightseeing", "Cultural Workshop"],
        food_preferences=["Vegetarian", "Local Traditional"],
        transportation_preferences=["Train", "Flight"],
        preferred_trip_duration=4,
    )
    db_session.add(pref)
    await db_session.commit()
    await db_session.refresh(pref)

    assert pref.preferred_destinations == ["Jaipur", "Ziro"]
    assert "History" in pref.interests
    assert pref.travel_style == "Cultural"
    assert pref.budget_range == "moderate"
    assert pref.preferred_trip_duration == 4

    out = UserTravelPreferenceOut.model_validate(pref)
    assert out.user_id == user.id
    assert out.preferred_destinations == ["Jaipur", "Ziro"]
    assert out.preferred_trip_duration == 4


@pytest.mark.asyncio
async def test_recommendation_scoring_formula_and_geometric_mean():
    """Verify the 6-factor multiplicative recommendation formula:
    score = (dest * int * bud * act * sty * hist)**(1/6) * 100
    """
    breakdown = MatchBreakdown(
        destination_match=0.90,
        interest_match=0.85,
        budget_match=1.00,
        activity_match=0.80,
        travel_style_match=0.95,
        historical_preference=0.90,
    )
    score = PersonalizedRecommendationEngine.compute_composite_score(breakdown)

    expected_product = 0.90 * 0.85 * 1.00 * 0.80 * 0.95 * 0.90
    expected_score = round(math.pow(expected_product, 1.0 / 6.0) * 100.0, 1)

    assert score == expected_score
    assert 85.0 <= score <= 95.0


@pytest.mark.asyncio
async def test_destination_recommendation_and_explainability(db_session: AsyncSession):
    """Test destination scoring and transparent explanation generation."""
    dest = Destination(
        name="Jaipur Royal Quarters",
        slug="jaipur-royal-quarters",
        state="Rajasthan",
        region="North",
        category="Culture · Heritage · Forts",
        best_season="Oct – Mar",
        budget="₹₹",
        trust_score=94,
        description="Imperial palaces, medieval astronomical observatories, and vibrant bazaars.",
        image_url="https://example.com/jaipur.jpg",
    )
    db_session.add(dest)
    await db_session.commit()

    pref = UserTravelPreference(
        user_id=uuid.uuid4(),
        preferred_destinations=["Jaipur"],
        interests=["Culture", "Heritage"],
        travel_style="Cultural",
        budget_range="moderate",
        preferred_accommodation=["Heritage Haveli"],
        preferred_activities=["Sightseeing"],
        food_preferences=["Vegetarian"],
        transportation_preferences=["Train"],
        preferred_trip_duration=4,
    )

    rec = PersonalizedRecommendationEngine.score_destination(dest, pref)
    assert rec.entity_type == "destination"
    assert rec.score >= 80.0
    assert "matches your interest in" in rec.explanation or "fits your selected" in rec.explanation
    assert rec.match_breakdown.destination_match >= 0.9
    assert rec.match_breakdown.interest_match >= 0.8


@pytest.mark.asyncio
async def test_hotel_recommendation_and_explainability(db_session: AsyncSession):
    """Test hotel scoring and accommodation type alignment."""
    dest = Destination(
        name="Heritage Town",
        slug="heritage-town",
        state="Rajasthan",
        region="North",
        category="Heritage",
        best_season="Winter",
        budget="₹₹",
        description="Old city.",
        image_url="https://example.com/town.jpg",
    )
    db_session.add(dest)
    await db_session.flush()

    hotel = Hotel(
        destination_id=dest.id,
        name="Alsisar Heritage Haveli",
        stay_type="Heritage Haveli",
        address="Sansar Chandra Road",
        price_level="₹₹",
        price_per_night="₹3,500",
        rating=4.8,
    )
    db_session.add(hotel)
    await db_session.commit()

    pref = UserTravelPreference(
        user_id=uuid.uuid4(),
        preferred_destinations=["Heritage Town"],
        interests=["History"],
        travel_style="Cultural",
        budget_range="moderate",
        preferred_accommodation=["Heritage Haveli"],
        preferred_activities=["Walking tours"],
        food_preferences=["Vegetarian"],
        transportation_preferences=["Flight"],
        preferred_trip_duration=3,
    )

    rec = PersonalizedRecommendationEngine.score_hotel(hotel, pref, target_destination="Heritage Town")
    assert rec.entity_type == "hotel"
    assert rec.score >= 80.0
    assert "offers your preferred Heritage Haveli accommodation" in rec.explanation
    assert "fits your moderate budget tier" in rec.explanation


@pytest.mark.asyncio
async def test_activity_and_restaurant_recommendations(db_session: AsyncSession):
    """Test activity and restaurant scoring with dietary and experiential matching."""
    dest = Destination(
        name="Majuli Island",
        slug="majuli-island",
        state="Assam",
        region="Northeast",
        category="River Island · Culture",
        best_season="Nov – Mar",
        budget="₹",
        description="Satras and bamboo crafts.",
        image_url="https://example.com/majuli.jpg",
    )
    db_session.add(dest)
    await db_session.flush()

    activity = Activity(
        destination_id=dest.id,
        title="Traditional Majuli Mask-Making Workshop",
        activity_type="Cultural Workshop",
        description="Learn ancient satra terracotta and bamboo mask craft.",
        duration_hours=2.5,
        price_range="₹500",
    )
    restaurant = Restaurant(
        destination_id=dest.id,
        name="Majuli Pure Veg Thali House",
        cuisine_type="Pure Vegetarian",
        address="Garamur Satra Road",
        price_range="₹",
        rating=4.7,
        must_try_dishes=["Assamese Joha Rice", "Alu Pitika", "Khar"],
    )
    db_session.add_all([activity, restaurant])
    await db_session.commit()

    pref = UserTravelPreference(
        user_id=uuid.uuid4(),
        preferred_destinations=["Majuli Island"],
        interests=["Culture", "Crafts"],
        travel_style="Cultural",
        budget_range="budget",
        preferred_accommodation=["Homestay"],
        preferred_activities=["Cultural Workshop"],
        food_preferences=["Vegetarian"],
        transportation_preferences=["Train"],
        preferred_trip_duration=3,
        dietary_needs="strictly_vegetarian",
    )

    act_rec = PersonalizedRecommendationEngine.score_activity(activity, pref)
    assert act_rec.entity_type == "activity"
    assert "matches your preferred activity in Cultural Workshop" in act_rec.explanation
    assert act_rec.score >= 80.0

    rest_rec = PersonalizedRecommendationEngine.score_restaurant(restaurant, pref)
    assert rest_rec.entity_type == "restaurant"
    assert "Vegetarian" in rest_rec.explanation
    assert rest_rec.score >= 75.0


@pytest.mark.asyncio
async def test_travel_preferences_crud_endpoints(client: AsyncClient):
    """Test GET and PATCH /api/v1/users/me/travel-preferences."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "pref.api.tester@khojai.in",
            "password": "Password123!",
            "full_name": "API Preference Tester",
        },
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET initial default preferences
    get_res = await client.get("/api/v1/users/me/travel-preferences", headers=headers)
    assert get_res.status_code == 200
    data = get_res.json()
    assert "budget_range" in data
    assert "preferred_trip_duration" in data

    # 2. PATCH modify preferences
    patch_payload = {
        "preferred_destinations": ["Jaipur", "Udaipur"],
        "interests": ["Architecture", "Heritage", "Folk Music"],
        "travel_style": "Cultural",
        "budget_range": "moderate",
        "preferred_accommodation": ["Heritage Haveli"],
        "preferred_activities": ["Sightseeing", "Guided Walk"],
        "food_preferences": ["Vegetarian", "Street food"],
        "preferred_trip_duration": 4,
    }
    patch_res = await client.patch("/api/v1/users/me/travel-preferences", json=patch_payload, headers=headers)
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["preferred_destinations"] == ["Jaipur", "Udaipur"]
    assert updated["preferred_trip_duration"] == 4
    assert updated["travel_style"] == "Cultural"
    assert updated["preferred_accommodation"] == ["Heritage Haveli"]

    # 3. GET verify persistence
    verify_res = await client.get("/api/v1/users/me/travel-preferences", headers=headers)
    assert verify_res.status_code == 200
    assert verify_res.json()["preferred_destinations"] == ["Jaipur", "Udaipur"]


@pytest.mark.asyncio
async def test_privacy_rejection_of_sensitive_data(client: AsyncClient):
    """Verify that attempting to store sensitive personal information is strictly rejected."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "privacy.test@khojai.in",
            "password": "Password123!",
            "full_name": "Privacy Guard User",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to send passport or card number
    bad_payload = {
        "interests": ["History"],
        "passport_number": "A12345678",
    }
    bad_res = await client.patch("/api/v1/users/me/travel-preferences", json=bad_payload, headers=headers)
    assert bad_res.status_code == 422
    assert "forbidden" in bad_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_travel_recommendations_endpoint(client: AsyncClient, db_session: AsyncSession):
    """Test GET /api/v1/travel/recommendations endpoint."""
    dest = Destination(
        name="Ziro Pine Valley",
        slug="ziro-pine-valley",
        state="Arunachal Pradesh",
        region="Northeast",
        category="Nature · Tribal Culture",
        best_season="Sep – Nov",
        budget="₹₹",
        trust_score=92,
        description="Apatani cultural landscapes and pine groves.",
        image_url="https://example.com/ziro.jpg",
    )
    db_session.add(dest)
    await db_session.commit()

    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "rec.tester@khojai.in",
            "password": "Password123!",
            "full_name": "Recommendation Tester",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    rec_res = await client.get("/api/v1/travel/recommendations?category=destinations&limit=3", headers=headers)
    assert rec_res.status_code == 200
    recs = rec_res.json()
    assert isinstance(recs, list)
    if recs:
        assert "score" in recs[0]
        assert "explanation" in recs[0]
        assert "match_breakdown" in recs[0]
        assert "destination_match" in recs[0]["match_breakdown"]


@pytest.mark.asyncio
async def test_ai_tools_personalization_integration(db_session: AsyncSession):
    """Test GetUserPreferencesTool and GetPersonalizedRecommendationsTool integration."""
    user = User(
        email="ai.agent.traveler@khojai.in",
        hashed_password="hashed_password",
        role="traveler",
        full_name="AI Agent Traveler",
    )
    db_session.add(user)
    await db_session.flush()

    pref = UserTravelPreference(
        user_id=user.id,
        preferred_destinations=["Ladakh"],
        interests=["High Altitude", "Photography", "Monasteries"],
        travel_style="Adventure",
        budget_range="luxury",
        preferred_accommodation=["Eco-Lodge"],
        preferred_activities=["Guided Trek"],
        food_preferences=["Local Traditional"],
        transportation_preferences=["Flight"],
        preferred_trip_duration=7,
    )
    db_session.add(pref)
    await db_session.commit()

    # 1. Test GetUserPreferencesTool
    tool = GetUserPreferencesTool()
    result = await tool.execute(user_id=str(user.id), session=db_session)
    assert result.success is True
    data = result.data
    assert data["travel_style"] == "Adventure"
    assert data["preferred_trip_duration"] == 7
    assert "Photography" in data["interests"]

    # 2. Test GetPersonalizedRecommendationsTool
    rec_tool = GetPersonalizedRecommendationsTool()
    rec_result = await rec_tool.execute(category="all", user_id=str(user.id), session=db_session, limit=3)
    assert rec_result.success is True
    assert isinstance(rec_result.data, list)

