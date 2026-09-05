"""Normalizers converting local database entities into provider-independent schemas for fallback."""

from typing import List, Optional
from backend.app.models.destination import Destination
from backend.app.travel.models.poi import Activity, Attraction, Hotel, Restaurant
from backend.app.travel.models.transit import Airport
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelHotel,
    TravelPlace,
)


class LocalDatabaseNormalizer:
    """Transforms local PostgreSQL/SQLite ORM models into provider-independent travel schemas."""

    @staticmethod
    def normalize_hotel(hotel: Hotel) -> TravelHotel:
        return TravelHotel(
            name=hotel.name,
            hotel_id=str(hotel.id),
            chain_code=None,
            latitude=hotel.latitude,
            longitude=hotel.longitude,
            address=hotel.address,
            city_name=getattr(hotel.city, "name", None) if getattr(hotel, "city", None) else None,
            country_code="IN",
            rating=hotel.rating,
            price_tier=hotel.price_level or "₹₹",
            price=None,
            currency="INR",
            amenities=hotel.amenities or [],
            photo_urls=[],
            provider="local_db",
            provider_id=str(hotel.id),
            booking_url=hotel.booking_url,
            metadata={
                "sustainability_rating": hotel.sustainability_rating,
                "stay_type": hotel.stay_type,
            },
        )

    @staticmethod
    def normalize_attraction_as_place(attraction: Attraction) -> TravelPlace:
        return TravelPlace(
            name=attraction.name,
            place_id=str(attraction.id),
            formatted_address=getattr(attraction.city, "name", None) if getattr(attraction, "city", None) else None,
            latitude=attraction.latitude,
            longitude=attraction.longitude,
            types=[attraction.category],
            rating=4.8,
            user_rating_count=50,
            price_level="₹",
            photos=[],
            reviews=[],
            phone_number=None,
            website_url=None,
            opening_hours=[attraction.timings] if attraction.timings else [],
            is_open_now=True,
            provider="local_db",
            provider_id=str(attraction.id),
            metadata={
                "difficulty": attraction.difficulty,
                "entry_fee": attraction.entry_fee,
                "tags": attraction.tags or [],
            },
        )

    @staticmethod
    def normalize_restaurant_as_place(restaurant: Restaurant) -> TravelPlace:
        return TravelPlace(
            name=restaurant.name,
            place_id=str(restaurant.id),
            formatted_address=restaurant.address,
            latitude=restaurant.latitude,
            longitude=restaurant.longitude,
            types=["restaurant", restaurant.cuisine_type],
            rating=restaurant.rating or 4.5,
            user_rating_count=30,
            price_level=restaurant.price_range or "₹",
            photos=[],
            reviews=[],
            phone_number=None,
            website_url=None,
            opening_hours=[restaurant.opening_hours] if restaurant.opening_hours else [],
            is_open_now=True,
            provider="local_db",
            provider_id=str(restaurant.id),
            metadata={"must_try_dishes": restaurant.must_try_dishes or []},
        )

    @staticmethod
    def normalize_activity(activity: Activity) -> TravelActivity:
        return TravelActivity(
            title=activity.title,
            description=activity.description,
            activity_type=activity.activity_type,
            duration=f"{activity.duration_hours} hours",
            price=None,
            currency="INR",
            latitude=None,
            longitude=None,
            rating=4.7,
            pictures=[],
            booking_url=None,
            provider="local_db",
            provider_id=str(activity.id),
        )

    @staticmethod
    def normalize_airport(airport: Airport) -> TravelAirport:
        return TravelAirport(
            name=airport.name,
            iata_code=airport.iata_code,
            icao_code=airport.icao_code,
            city_name=getattr(airport.city, "name", None) if getattr(airport, "city", None) else None,
            country_code="IN",
            latitude=airport.latitude,
            longitude=airport.longitude,
            provider="local_db",
        )
