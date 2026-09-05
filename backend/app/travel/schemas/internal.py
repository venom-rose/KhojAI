"""Provider-independent internal travel schemas for KHOJAI.

Guarantees provider response structures (Amadeus, Google Places, etc.)
do not leak across application boundaries.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TravelPhoto(BaseModel):
    """Normalized photo attribution & proxy reference."""
    photo_reference: str = Field(..., description="Provider reference id or resource name")
    height: Optional[int] = None
    width: Optional[int] = None
    author_attributions: List[str] = Field(default_factory=list)
    proxy_url: Optional[str] = None


class TravelReview(BaseModel):
    """Normalized review snippet where permitted."""
    author_name: str
    rating: Optional[float] = None
    text: Optional[str] = None
    relative_publish_time: Optional[str] = None
    language: Optional[str] = None


class TravelHotel(BaseModel):
    """Provider-independent hotel representation."""
    model_config = ConfigDict(from_attributes=True)

    name: str
    hotel_id: Optional[str] = None
    chain_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    city_name: Optional[str] = None
    country_code: Optional[str] = None
    rating: Optional[float] = None
    price_tier: Optional[str] = None  # '₹', '₹₹', '₹₹₹'
    price: Optional[float] = None
    currency: str = "INR"
    amenities: List[str] = Field(default_factory=list)
    photo_urls: List[str] = Field(default_factory=list)
    provider: str = Field(..., description="E.g. 'amadeus', 'google_places', 'local_db'")
    provider_id: Optional[str] = None
    booking_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TravelPlace(BaseModel):
    """Provider-independent place / Point-of-Interest representation."""
    model_config = ConfigDict(from_attributes=True)

    name: str
    place_id: Optional[str] = None
    formatted_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    types: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    price_level: Optional[str] = None
    photos: List[TravelPhoto] = Field(default_factory=list)
    reviews: List[TravelReview] = Field(default_factory=list)
    phone_number: Optional[str] = None
    website_url: Optional[str] = None
    opening_hours: List[str] = Field(default_factory=list)
    is_open_now: Optional[bool] = None
    provider: str = Field(..., description="E.g. 'google_places', 'amadeus', 'local_db'")
    provider_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TravelPlaceAutocompleteItem(BaseModel):
    """Predictive search autocomplete suggestion."""
    place_id: str
    primary_text: str
    secondary_text: Optional[str] = None
    full_text: str
    types: List[str] = Field(default_factory=list)
    provider: str = "google_places"


class TravelFlightSegment(BaseModel):
    """Flight leg or segment."""
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    carrier_code: str
    flight_number: str
    duration: Optional[str] = None


class TravelFlight(BaseModel):
    """Provider-independent flight offer representation."""
    model_config = ConfigDict(from_attributes=True)

    offer_id: str
    airline_code: str
    airline_name: Optional[str] = None
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    duration: str
    stops: int = 0
    price: float
    currency: str = "INR"
    segments: List[TravelFlightSegment] = Field(default_factory=list)
    booking_url: Optional[str] = None
    provider: str = "amadeus"


class TravelActivity(BaseModel):
    """Provider-independent activity or experiential tour."""
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: Optional[str] = None
    activity_type: Optional[str] = None
    duration: Optional[str] = None
    price: Optional[float] = None
    currency: str = "INR"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    pictures: List[str] = Field(default_factory=list)
    booking_url: Optional[str] = None
    provider: str = Field(..., description="E.g. 'amadeus', 'local_db'")
    provider_id: Optional[str] = None


class TravelAirport(BaseModel):
    """Provider-independent airport or transit hub."""
    model_config = ConfigDict(from_attributes=True)

    name: str
    iata_code: str
    icao_code: Optional[str] = None
    city_name: Optional[str] = None
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    provider: str = Field(..., description="E.g. 'amadeus', 'local_db'")
