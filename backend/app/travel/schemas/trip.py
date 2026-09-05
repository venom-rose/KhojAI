"""Trip and User Travel Preference Pydantic Schemas."""

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------
# User Travel Preference Schemas
# ---------------------------------------------------------

class UserTravelPreferenceBase(BaseModel):
    budget_preference: str = Field(default="₹₹", max_length=10)
    preferred_pace: str = Field(default="balanced", max_length=20)
    travel_styles: List[str] = Field(default_factory=lambda: ["Slow travel", "Culture-led"])
    dietary_needs: str = Field(default="none", max_length=50)
    fitness_level: str = Field(default="moderate", max_length=30)
    preferred_stay_types: List[str] = Field(default_factory=lambda: ["Homestay", "Eco-Lodge"])
    preferred_regions: List[str] = Field(default_factory=lambda: ["Himalayas", "Northeast"])


class UserTravelPreferenceCreate(UserTravelPreferenceBase):
    user_id: Optional[uuid.UUID] = None


class UserTravelPreferenceUpdate(BaseModel):
    budget_preference: Optional[str] = None
    preferred_pace: Optional[str] = None
    travel_styles: Optional[List[str]] = None
    dietary_needs: Optional[str] = None
    fitness_level: Optional[str] = None
    preferred_stay_types: Optional[List[str]] = None
    preferred_regions: Optional[List[str]] = None


class UserTravelPreferenceOut(UserTravelPreferenceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------
# Trip Item Schemas
# ---------------------------------------------------------

class TripItemBase(BaseModel):
    item_type: str = Field(..., description="'attraction', 'activity', 'hotel', 'restaurant', 'transit', 'custom'")
    attraction_id: Optional[uuid.UUID] = None
    hotel_id: Optional[uuid.UUID] = None
    restaurant_id: Optional[uuid.UUID] = None
    activity_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    estimated_cost: Optional[str] = None
    sort_order: int = Field(default=1, ge=1)


class TripItemCreate(TripItemBase):
    trip_day_id: Optional[uuid.UUID] = None


class TripItemUpdate(BaseModel):
    item_type: Optional[str] = None
    attraction_id: Optional[uuid.UUID] = None
    hotel_id: Optional[uuid.UUID] = None
    restaurant_id: Optional[uuid.UUID] = None
    activity_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    estimated_cost: Optional[str] = None
    sort_order: Optional[int] = None


class TripItemOut(TripItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_day_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------
# Trip Day Schemas
# ---------------------------------------------------------

class TripDayBase(BaseModel):
    day_number: int = Field(..., ge=1)
    day_date: Optional[date] = None
    theme_title: str = Field(..., min_length=1, max_length=200)
    notes: Optional[str] = None


class TripDayCreate(TripDayBase):
    trip_id: Optional[uuid.UUID] = None
    items: Optional[List[TripItemCreate]] = Field(default_factory=list)


class TripDayUpdate(BaseModel):
    day_number: Optional[int] = None
    day_date: Optional[date] = None
    theme_title: Optional[str] = None
    notes: Optional[str] = None


class TripDayOut(TripDayBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    trip_id: uuid.UUID
    items: List[TripItemOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------
# Trip Schemas
# ---------------------------------------------------------

class TripBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    destination_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_days: int = Field(default=5, ge=1, le=60)
    budget_tier: str = Field(default="₹₹", max_length=20)
    status: str = Field(default="draft", max_length=30)
    is_public: bool = Field(default=False)


class TripCreate(TripBase):
    user_id: Optional[uuid.UUID] = None
    days: Optional[List[TripDayCreate]] = Field(default_factory=list)


class TripUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    destination_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_days: Optional[int] = None
    budget_tier: Optional[str] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None


class TripOut(TripBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    share_token: str
    days: List[TripDayOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TripSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    destination_id: Optional[uuid.UUID] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_days: int
    budget_tier: str
    status: str
    is_public: bool
    share_token: str
    days_count: int = 0
    created_at: datetime
    updated_at: datetime
