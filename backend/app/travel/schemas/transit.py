"""Pydantic schemas for transit and routing entities."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AirportBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    iata_code: str = Field(..., min_length=3, max_length=3)
    icao_code: Optional[str] = Field(None, max_length=4)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_international: bool = Field(default=False)


class AirportCreate(AirportBase):
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


AirportCreateIn = AirportCreate


class AirportUpdate(BaseModel):
    name: Optional[str] = None
    iata_code: Optional[str] = None
    icao_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_international: Optional[bool] = None
    city_id: Optional[uuid.UUID] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class AirportOut(AirportBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    city_id: Optional[uuid.UUID] = None
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class TransportationOptionBase(BaseModel):
    transport_type: str = Field(..., min_length=1, max_length=50)
    origin_name: str = Field(..., min_length=1, max_length=150)
    destination_name: str = Field(..., min_length=1, max_length=150)
    duration_hours: float = Field(..., gt=0)
    cost_estimate: str = Field(..., min_length=1, max_length=100)
    frequency: str = Field(default="Daily", max_length=100)
    operator_name: Optional[str] = Field(None, max_length=150)
    booking_tips: Optional[str] = None


class TransportationOptionCreate(TransportationOptionBase):
    destination_id: uuid.UUID
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


TransportationOptionCreateIn = TransportationOptionCreate


class TransportationOptionUpdate(BaseModel):
    transport_type: Optional[str] = None
    origin_name: Optional[str] = None
    destination_name: Optional[str] = None
    duration_hours: Optional[float] = None
    cost_estimate: Optional[str] = None
    frequency: Optional[str] = None
    operator_name: Optional[str] = None
    booking_tips: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class TransportationOptionOut(TransportationOptionBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    destination_id: uuid.UUID
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class TravelRouteBase(BaseModel):
    route_name: str = Field(..., min_length=1, max_length=200)
    mode: str = Field(default="Road", max_length=50)
    distance_km: float = Field(..., gt=0)
    typical_duration_hours: float = Field(..., gt=0)
    road_condition: str = Field(default="Metalled two-lane highway with mountain curves", max_length=100)
    scenic_rating: int = Field(default=9, ge=1, le=10)
    seasonal_notes: Optional[str] = None


class TravelRouteCreate(TravelRouteBase):
    destination_id: uuid.UUID
    origin_city_id: Optional[uuid.UUID] = None
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


TravelRouteCreateIn = TravelRouteCreate


class TravelRouteUpdate(BaseModel):
    route_name: Optional[str] = None
    mode: Optional[str] = None
    distance_km: Optional[float] = None
    typical_duration_hours: Optional[float] = None
    road_condition: Optional[str] = None
    scenic_rating: Optional[int] = None
    seasonal_notes: Optional[str] = None
    origin_city_id: Optional[uuid.UUID] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class TravelRouteOut(TravelRouteBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    destination_id: uuid.UUID
    origin_city_id: Optional[uuid.UUID] = None
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
