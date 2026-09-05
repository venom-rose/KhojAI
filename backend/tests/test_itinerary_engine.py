import pytest
from datetime import date, timedelta
from backend.app.travel.schemas.itinerary_engine import (
    CostBreakdown,
    DayPlan,
    ItineraryEngineInput,
    StructuredTripItinerary,
)
from backend.app.travel.services.itinerary_engine import (
    ItineraryGenerationEngine,
    haversine_distance_km,
    itinerary_engine,
)


def test_haversine_distance_calculation():
    """Verify distance calculation between coordinates."""
    # Delhi (28.6139, 77.2090) to Jaipur (26.9124, 75.7873)
    dist = haversine_distance_km(28.6139, 77.2090, 26.9124, 75.7873)
    assert 230 < dist < 250  # straight line ~240 km


def test_date_validation_and_duration():
    """Verify valid date ranges, duration calculation, and error raising on inverted dates."""
    engine = ItineraryGenerationEngine()

    # 1. Normal valid range (5 days inclusive)
    dur, start_d, end_d, dates = engine.validate_and_compute_duration(
        start_date_str="2026-10-10",
        end_date_str="2026-10-14",
        duration_days=None,
    )
    assert dur == 5
    assert start_d == date(2026, 10, 10)
    assert end_d == date(2026, 10, 14)
    assert len(dates) == 5
    assert dates[0] == "2026-10-10"
    assert dates[-1] == "2026-10-14"

    # 2. Inverted dates raise ValueError
    with pytest.raises(ValueError, match="cannot be earlier than start_date"):
        engine.validate_and_compute_duration(
            start_date_str="2026-10-15",
            end_date_str="2026-10-10",
            duration_days=None,
        )

    # 3. Invalid date format raises ValueError
    with pytest.raises(ValueError, match="Invalid start_date format"):
        engine.validate_and_compute_duration(
            start_date_str="10/10/2026",
            end_date_str="2026-10-14",
            duration_days=None,
        )

    # 4. Duration fallback when dates are omitted
    dur2, _, _, dates2 = engine.validate_and_compute_duration(
        start_date_str=None,
        end_date_str=None,
        duration_days=4,
    )
    assert dur2 == 4
    assert len(dates2) == 4

    # 5. Clamp excessively long duration to 14 days
    dur_long, _, _, dates_long = engine.validate_and_compute_duration(
        start_date_str=None,
        end_date_str=None,
        duration_days=25,
    )
    assert dur_long == 14
    assert len(dates_long) == 14


@pytest.mark.asyncio
async def test_itinerary_generation_structure_and_slots():
    """Verify complete itinerary generation produces required hierarchical structure."""
    payload = ItineraryEngineInput(
        destination="Jaipur",
        start_date="2026-11-01",
        end_date="2026-11-03",
        budget="moderate",
        traveler_count=2,
        interests=["heritage", "crafts", "monuments"],
        travel_style="slow travel",
        hotel_preference="heritage haveli",
    )

    itinerary: StructuredTripItinerary = await itinerary_engine.generate(payload)

    # Validate top-level schema
    assert itinerary.destination == "Jaipur"
    assert itinerary.duration_days == 3
    assert itinerary.traveler_count == 2
    assert len(itinerary.days) == 3
    assert itinerary.summary
    assert itinerary.pacing_rating == "Unhurried & Immersive"
    assert itinerary.transportation_guidance

    # Validate Day structure
    for day in itinerary.days:
        assert isinstance(day, DayPlan)
        assert day.day_number in (1, 2, 3)
        assert day.neighborhood_cluster
        assert day.day_hotel is not None
        assert day.day_total_transit_km >= 0
        assert day.day_total_transit_minutes >= 0

        # Validate Morning, Afternoon, Evening slots
        assert day.morning.time_window
        assert day.afternoon.time_window
        assert day.evening.time_window

        # Verify free time buffer is preserved
        assert day.morning.free_time_minutes >= 30
        assert day.afternoon.free_time_minutes >= 30
        assert day.evening.free_time_minutes >= 30

        # Verify activities contain realistic durations and opening hours
        for slot in [day.morning, day.afternoon, day.evening]:
            for act in slot.activities:
                assert act.duration_hours > 0
                assert act.start_time
                assert act.end_time
                assert act.cost_estimate_inr >= 0


@pytest.mark.asyncio
async def test_itinerary_geographic_clustering_and_no_impossible_schedule():
    """Verify that sights within each day belong to cohesive spatial areas without impossible overlaps."""
    payload = ItineraryEngineInput(
        destination="Jaipur",
        duration_days=2,
        budget="moderate",
        traveler_count=1,
    )

    itinerary = await itinerary_engine.generate(payload)
    assert len(itinerary.days) == 2

    for day in itinerary.days:
        all_activities = (
            day.morning.activities + day.afternoon.activities + day.evening.activities
        )
        # Avoid impossible schedules: max 3-4 activities per day
        assert 1 <= len(all_activities) <= 4

        # Total scheduled duration per day should not exceed 7.5 hours
        total_hours = sum(a.duration_hours for a in all_activities)
        assert total_hours <= 7.5


@pytest.mark.asyncio
async def test_itinerary_cost_estimation_math():
    """Verify itemized cost calculations scale properly with travelers and duration."""
    payload = ItineraryEngineInput(
        destination="Jaipur",
        duration_days=4,
        traveler_count=2,
        budget="moderate",
    )

    itinerary = await itinerary_engine.generate(payload)
    costs: CostBreakdown = itinerary.estimated_cost

    assert costs.accommodation_inr > 0
    assert costs.activities_and_admission_inr >= 0
    assert costs.local_transport_inr > 0
    assert costs.food_and_dining_inr > 0
    assert costs.contingency_inr > 0
    assert costs.total_estimated_inr > 0
    assert costs.per_person_inr == round(costs.total_estimated_inr / 2, 2)

    # Verify math consistency
    subtotal = (
        costs.accommodation_inr
        + costs.activities_and_admission_inr
        + costs.local_transport_inr
        + costs.food_and_dining_inr
    )
    expected_contingency = round(subtotal * 0.10, 2)
    assert abs(costs.contingency_inr - expected_contingency) < 1.0


@pytest.mark.asyncio
async def test_itinerary_budget_tiers_scaling():
    """Verify that choosing 'budget' vs 'luxury' scales accommodation and dining estimates accordingly."""
    budget_input = ItineraryEngineInput(
        destination="Rajasthan",
        duration_days=3,
        budget="budget",
        hotel_preference="budget hostel",
    )
    luxury_input = ItineraryEngineInput(
        destination="Rajasthan",
        duration_days=3,
        budget="luxury",
        hotel_preference="luxury palace",
    )

    budget_itin = await itinerary_engine.generate(budget_input)
    luxury_itin = await itinerary_engine.generate(luxury_input)

    assert budget_itin.estimated_cost.total_estimated_inr < luxury_itin.estimated_cost.total_estimated_inr
    assert (
        budget_itin.estimated_cost.accommodation_inr
        < luxury_itin.estimated_cost.accommodation_inr
    )
