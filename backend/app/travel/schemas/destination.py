"""Pydantic schemas for destination classifications, seasons, and expanded travel intelligence."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.travel.schemas.poi import ActivityOut, AttractionOut, HotelOut, RestaurantOut
from backend.app.travel.schemas.transit import TransportationOptionOut, TravelRouteOut


class DestinationCategoryBase(BaseModel):
    slug: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=150)
    description: Optional[str] = None
    icon_name: Optional[str] = Field(default="Compass", max_length=50)


class DestinationCategoryCreate(DestinationCategoryBase):
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


DestinationCategoryCreateIn = DestinationCategoryCreate


class DestinationCategoryUpdate(BaseModel):
    slug: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    icon_name: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class DestinationCategoryOut(DestinationCategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class SeasonBase(BaseModel):
    season_name: str = Field(..., min_length=1, max_length=50)
    start_month: int = Field(..., ge=1, le=12)
    end_month: int = Field(..., ge=1, le=12)
    weather_summary: str = Field(..., min_length=1)
    avg_temp_min_c: Optional[float] = None
    avg_temp_max_c: Optional[float] = None
    rainfall_level: str = Field(default="moderate", max_length=20)
    is_recommended: bool = Field(default=True)
    advisory_notes: Optional[str] = None


class SeasonCreate(SeasonBase):
    destination_id: uuid.UUID
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


SeasonCreateIn = SeasonCreate


class SeasonUpdate(BaseModel):
    season_name: Optional[str] = None
    start_month: Optional[int] = None
    end_month: Optional[int] = None
    weather_summary: Optional[str] = None
    avg_temp_min_c: Optional[float] = None
    avg_temp_max_c: Optional[float] = None
    rainfall_level: Optional[str] = None
    is_recommended: Optional[bool] = None
    advisory_notes: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class SeasonOut(SeasonBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    destination_id: uuid.UUID
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class TravelTipBase(BaseModel):
    category: str = Field(default="logistics", max_length=50)
    title: str = Field(..., min_length=1, max_length=150)
    content: str = Field(..., min_length=1)
    priority: int = Field(default=1, ge=1, le=5)


class TravelTipCreate(TravelTipBase):
    destination_id: uuid.UUID
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


TravelTipCreateIn = TravelTipCreate


class TravelTipUpdate(BaseModel):
    category: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    priority: Optional[int] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class TravelTipOut(TravelTipBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    destination_id: uuid.UUID
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class DestinationDetailExpandedOut(BaseModel):
    """Complete, rich destination intelligence payload aggregating all child entities."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    state: str
    region: str
    category: str
    best_season: str
    budget: str
    trust_score: int
    description: str
    image_url: str
    accent_color: str
    coordinate_x: str
    coordinate_y: str
    demo_note: str

    # Geo coordinates & logistics
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    country_id: Optional[uuid.UUID] = None
    state_id: Optional[uuid.UUID] = None
    city_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    is_hidden_gem: bool = True

    # Provenance
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None

    # Child lists
    tags: List[str] = Field(default_factory=list)
    seasons: List[SeasonOut] = Field(default_factory=list)
    tips: List[TravelTipOut] = Field(default_factory=list)
    attractions: List[AttractionOut] = Field(default_factory=list)
    hotels: List[HotelOut] = Field(default_factory=list)
    restaurants: List[RestaurantOut] = Field(default_factory=list)
    activities: List[ActivityOut] = Field(default_factory=list)
    transportation_options: List[TransportationOptionOut] = Field(default_factory=list)
    routes: List[TravelRouteOut] = Field(default_factory=list)
