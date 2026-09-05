from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ItineraryEngineInput(BaseModel):
    """Input payload for deterministic itinerary generation."""
    destination: str = Field(..., description="Target destination or city (e.g. 'Jaipur', 'Rajasthan', 'Spiti')")
    start_date: Optional[str] = Field(None, description="Trip start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="Trip end date in YYYY-MM-DD format")
    duration_days: Optional[int] = Field(None, description="Trip duration in days (used if dates omitted)")
    budget: Optional[str] = Field("moderate", description="Budget tier or maximum budget (e.g. '₹25,000', 'budget', 'moderate', 'luxury')")
    traveler_count: int = Field(1, ge=1, le=20, description="Number of travelers")
    interests: List[str] = Field(default_factory=list, description="Traveler interests (e.g. ['heritage', 'nature', 'food', 'crafts', 'monuments'])")
    travel_style: str = Field("relaxed", description="Pacing and style (e.g. 'relaxed', 'moderate', 'fast', 'slow travel', 'adventure')")
    hotel_preference: str = Field("boutique homestay", description="Lodging preference (e.g. 'homestay', 'mid-tier hotel', 'heritage haveli', 'budget hostel')")
    activity_preferences: List[str] = Field(default_factory=list, description="Preferred activity types (e.g. ['walking tour', 'cooking workshop', 'monuments'])")
    transport_preferences: str = Field("private cab / train", description="Preferred transit mode (e.g. 'private cab', 'self-drive', 'train/public')")

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Destination cannot be empty.")
        return clean


class TimeSlotActivity(BaseModel):
    """Activity or experience planned within a daily time slot."""
    title: str = Field(..., description="Activity title or main highlight")
    place_name: Optional[str] = Field(None, description="Name of the attraction, venue, or site")
    category: str = Field("sightseeing", description="Category (monument, nature, food, workshop, leisure)")
    start_time: str = Field(..., description="Planned start time (e.g. '09:30 AM')")
    end_time: str = Field(..., description="Planned end time (e.g. '12:00 PM')")
    duration_hours: float = Field(..., description="Estimated visit duration in hours")
    description: str = Field(..., description="Details and context on what to experience")
    cost_estimate_inr: float = Field(0.0, description="Estimated admission, activity, or meal cost in INR")
    latitude: Optional[float] = Field(None, description="Geographic latitude")
    longitude: Optional[float] = Field(None, description="Geographic longitude")
    opening_hours: Optional[str] = Field(None, description="Operating hours advisory")
    transit_from_previous: Optional[Dict[str, Any]] = Field(
        None,
        description="Transit details from the previous activity (distance_km, drive_minutes, mode)",
    )


class DayScheduleSlot(BaseModel):
    """Detailed slot within a day (Morning, Afternoon, Evening)."""
    time_window: str = Field(..., description="Time window (e.g. '09:00 AM - 01:00 PM')")
    theme: str = Field(..., description="Main focus or theme of this time slot")
    activities: List[TimeSlotActivity] = Field(default_factory=list, description="Activities in this slot")
    free_time_minutes: int = Field(..., description="Built-in leisure buffer minutes for unhurried pacing")
    culinary_recommendation: Optional[str] = Field(None, description="Recommended dining or refreshments")


class DayPlan(BaseModel):
    """Complete day plan in the itinerary."""
    day_number: int = Field(..., description="1-indexed day number")
    date_str: Optional[str] = Field(None, description="Calendar date if available (YYYY-MM-DD)")
    title: str = Field(..., description="Headline theme for the day")
    neighborhood_cluster: str = Field(..., description="Geographic focus area for the day (e.g. 'Old Walled City & City Palace Area')")
    morning: DayScheduleSlot = Field(..., description="Morning schedule slot")
    afternoon: DayScheduleSlot = Field(..., description="Afternoon schedule slot")
    evening: DayScheduleSlot = Field(..., description="Evening schedule slot")
    day_hotel: Optional[Dict[str, Any]] = Field(None, description="Recommended hotel for this night")
    day_total_transit_km: float = Field(0.0, description="Total transit distance for the day")
    day_total_transit_minutes: int = Field(0, description="Total transit time in minutes")


class CostBreakdown(BaseModel):
    """Transparent itemized cost estimates."""
    accommodation_inr: float = Field(..., description="Total lodging costs across all nights")
    activities_and_admission_inr: float = Field(..., description="Admission fees and activity costs")
    local_transport_inr: float = Field(..., description="Local cab, auto-rickshaw, or fuel transit estimate")
    food_and_dining_inr: float = Field(..., description="Estimated dining, street food, and cafes")
    contingency_inr: float = Field(..., description="Recommended buffer for miscellaneous expenses")
    total_estimated_inr: float = Field(..., description="Grand total estimated cost for all travelers")
    per_person_inr: float = Field(..., description="Estimated cost per traveler")
    currency: str = Field("INR", description="Currency symbol/code")
    pricing_disclaimer: str = Field(
        "Estimated budget based on local verified reference benchmarks. Excludes long-distance domestic flights/trains.",
        description="Anti-hallucination pricing notice",
    )


class StructuredTripItinerary(BaseModel):
    """Hierarchical structured trip output returned by the itinerary engine."""
    summary: str = Field(..., description="Executive narrative summarizing the trip focus and pacing")
    destination: str = Field(..., description="Primary destination or region")
    duration_days: int = Field(..., description="Total duration in days")
    start_date: Optional[str] = Field(None, description="Start date")
    end_date: Optional[str] = Field(None, description="End date")
    traveler_count: int = Field(1, description="Number of travelers")
    budget_tier: str = Field(..., description="Requested or normalized budget tier")
    estimated_cost: CostBreakdown = Field(..., description="Itemized estimated cost breakdown")
    days: List[DayPlan] = Field(..., description="Day-by-day scheduled plans (Day 1, Day 2, etc.)")
    pacing_rating: str = Field("Unhurried & Immersive", description="Evaluation of itinerary pacing")
    transportation_guidance: Dict[str, Any] = Field(default_factory=dict, description="Transit hub and local commute advice")
    curator_notes: List[str] = Field(default_factory=list, description="Authentic local travel tips and cultural etiquette")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
