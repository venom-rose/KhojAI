"""Pydantic schemas for Points of Interest (Attractions, Activities, Hotels, Restaurants)."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AttractionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    category: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    entry_fee: str = Field(default="Free", max_length=50)
    timings: str = Field(default="Sunrise to Sunset", max_length=100)
    difficulty: str = Field(default="Easy", max_length=30)
    recommended_duration_mins: int = Field(default=120)
    tags: List[str] = Field(default_factory=list)


class AttractionCreate(AttractionBase):
    destination_id: uuid.UUID
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


AttractionCreateIn = AttractionCreate


class AttractionUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    entry_fee: Optional[str] = None
    timings: Optional[str] = None
    difficulty: Optional[str] = None
    recommended_duration_mins: Optional[int] = None
    tags: Optional[List[str]] = None
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class AttractionOut(AttractionBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    destination_id: uuid.UUID
    city_id: Optional[uuid.UUID] = None
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class ActivityBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    activity_type: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    duration_hours: float = Field(default=2.5)
    price_range: str = Field(default="₹300 – ₹800", max_length=50)
    seasonality: str = Field(default="All year", max_length=100)
    guide_required: bool = Field(default=True)


class ActivityCreate(ActivityBase):
    destination_id: uuid.UUID
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


ActivityCreateIn = ActivityCreate


class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    activity_type: Optional[str] = None
    description: Optional[str] = None
    duration_hours: Optional[float] = None
    price_range: Optional[str] = None
    seasonality: Optional[str] = None
    guide_required: Optional[bool] = None
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class ActivityOut(ActivityBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    destination_id: uuid.UUID
    city_id: Optional[uuid.UUID] = None
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class HotelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    stay_type: str = Field(default="Homestay", max_length=50)
    address: str = Field(..., min_length=1, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_per_night: str = Field(default="₹1,500 – ₹2,500", max_length=100)
    price_level: str = Field(default="₹₹", max_length=5)
    rating: Optional[float] = Field(default=4.7, ge=0.0, le=5.0)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[str] = Field(None, max_length=100)
    booking_url: Optional[str] = Field(None, max_length=500)
    amenities: List[str] = Field(default_factory=list)
    sustainability_rating: int = Field(default=90, ge=0, le=100)


class HotelCreate(HotelBase):
    destination_id: uuid.UUID
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


HotelCreateIn = HotelCreate


class HotelUpdate(BaseModel):
    name: Optional[str] = None
    stay_type: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_per_night: Optional[str] = None
    price_level: Optional[str] = None
    rating: Optional[float] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    booking_url: Optional[str] = None
    amenities: Optional[List[str]] = None
    sustainability_rating: Optional[int] = None
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class HotelOut(HotelBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    destination_id: uuid.UUID
    city_id: Optional[uuid.UUID] = None
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class RestaurantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    cuisine_type: str = Field(..., min_length=1, max_length=100)
    address: str = Field(..., min_length=1, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_range: str = Field(default="₹", max_length=10)
    rating: Optional[float] = Field(default=4.5, ge=0.0, le=5.0)
    must_try_dishes: List[str] = Field(default_factory=list)
    opening_hours: str = Field(default="11:00 AM – 8:30 PM", max_length=100)


class RestaurantCreate(RestaurantBase):
    destination_id: uuid.UUID
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


RestaurantCreateIn = RestaurantCreate


class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    cuisine_type: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_range: Optional[str] = None
    rating: Optional[float] = None
    must_try_dishes: Optional[List[str]] = None
    opening_hours: Optional[str] = None
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class RestaurantOut(RestaurantBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    destination_id: uuid.UUID
    city_id: Optional[uuid.UUID] = None
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
