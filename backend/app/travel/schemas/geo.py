"""Pydantic schemas for geographic entities."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CountryBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 code (e.g. 'IN')")
    name: str = Field(..., min_length=1, max_length=100)
    currency: str = Field(default="INR", max_length=3)
    phone_code: Optional[str] = Field(default="+91", max_length=10)
    continent: str = Field(default="Asia", max_length=50)


class CountryCreate(CountryBase):
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


CountryCreateIn = CountryCreate


class CountryUpdate(BaseModel):
    name: Optional[str] = None
    currency: Optional[str] = None
    phone_code: Optional[str] = None
    continent: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class CountryOut(CountryBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class StateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=10)
    region: str = Field(..., min_length=1, max_length=100)


class StateCreate(StateBase):
    country_id: uuid.UUID
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


StateCreateIn = StateCreate


class StateUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    region: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class StateOut(StateBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    country_id: uuid.UUID
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class CityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    city_code: Optional[str] = Field(None, max_length=10)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_meters: Optional[int] = None


class CityCreate(CityBase):
    state_id: uuid.UUID
    source: Optional[str] = "seed_verified"
    source_id: Optional[str] = None


CityCreateIn = CityCreate


class CityUpdate(BaseModel):
    name: Optional[str] = None
    city_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    elevation_meters: Optional[int] = None
    source: Optional[str] = None
    source_id: Optional[str] = None


class CityOut(CityBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    state_id: uuid.UUID
    created_at: datetime
    source: Optional[str] = None
    source_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
