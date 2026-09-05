"""Unit and integration tests for Travel Data Providers, Normalizers, Caching, and Endpoints."""

import asyncio
import time
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.destination import Destination
from backend.app.travel.cache.cache_manager import TravelCacheManager
from backend.app.travel.models.geo import City, Country, State
from backend.app.travel.models.poi import Activity, Attraction, Hotel, Restaurant
from backend.app.travel.models.transit import Airport
from backend.app.travel.normalizers.amadeus_normalizer import AmadeusNormalizer
from backend.app.travel.normalizers.airlabs_normalizer import AirLabsNormalizer
from backend.app.travel.normalizers.google_normalizer import GooglePlacesNormalizer
from backend.app.travel.normalizers.local_normalizer import LocalDatabaseNormalizer
from backend.app.travel.providers.amadeus_provider import AmadeusProvider  # deprecated but kept
from backend.app.travel.providers.airlabs_provider import AirLabsProvider
from backend.app.travel.providers.google_places_provider import GooglePlacesProvider
from backend.app.travel.providers.local_db_provider import LocalDatabaseProvider
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)
from backend.app.travel.services.travel_provider_service import TravelProviderService


# ---------------------------------------------------------------------------
# 1. Internal Schemas & Data Contracts
# ---------------------------------------------------------------------------

def test_internal_schemas_instantiation():
    hotel = TravelHotel(
        name="Donyi Hango Apatani Homestay",
        hotel_id="hotel-123",
        address="Hong Village, Ziro",
        rating=4.8,
        price_tier="₹₹",
        provider="local_db",
    )
    assert hotel.name == "Donyi Hango Apatani Homestay"
    assert hotel.provider == "local_db"
    assert hotel.currency == "INR"

    flight = TravelFlight(
        offer_id="FL-999",
        airline_code="6E",
        airline_name="IndiGo",
        departure_airport="DEL",
        arrival_airport="GAU",
        departure_time="2026-10-15T06:00:00",
        arrival_time="2026-10-15T08:30:00",
        duration="2h 30m",
        stops=0,
        price=4500.0,
        provider="amadeus",
    )
    assert flight.stops == 0
    assert flight.price == 4500.0

    place = TravelPlace(
        name="Hong Village Lapang",
        formatted_address="Ziro, Arunachal Pradesh",
        types=["heritage", "cultural_landmark"],
        rating=4.9,
        provider="google_places",
    )
    assert place.rating == 4.9
    assert place.provider == "google_places"


# ---------------------------------------------------------------------------
# 2. Normalizers Testing
# ---------------------------------------------------------------------------

def test_amadeus_normalizer_hotels():
    mock_payload = {
        "data": [
            {
                "hotelId": "MCDEL123",
                "name": "Courtyard Marriott",
                "geoCode": {"latitude": 28.5562, "longitude": 77.0999},
                "address": {"cityName": "New Delhi", "countryCode": "IN", "lines": ["Near IGI Airport"]},
                "rating": "4",
                "amenities": ["WIFI", "PARKING"],
            }
        ]
    }
    hotels = AmadeusNormalizer.normalize_hotels(mock_payload)
    assert len(hotels) == 1
    assert hotels[0].name == "Courtyard Marriott"
    assert hotels[0].hotel_id == "MCDEL123"
    assert hotels[0].latitude == 28.5562
    assert hotels[0].provider == "amadeus"


def test_amadeus_normalizer_flights():
    mock_payload = {
        "data": [
            {
                "id": "1",
                "price": {"total": "5200.00", "currency": "INR"},
                "itineraries": [
                    {
                        "duration": "PT2H35M",
                        "segments": [
                            {
                                "departure": {"iataCode": "DEL", "at": "2026-10-10T06:00:00"},
                                "arrival": {"iataCode": "GAU", "at": "2026-10-10T08:35:00"},
                                "carrierCode": "6E",
                                "number": "204",
                                "duration": "PT2H35M",
                            }
                        ],
                    }
                ],
            }
        ],
        "dictionaries": {"carriers": {"6E": "IndiGo"}},
    }
    flights = AmadeusNormalizer.normalize_flights(mock_payload)
    assert len(flights) == 1
    assert flights[0].departure_airport == "DEL"
    assert flights[0].arrival_airport == "GAU"
    assert flights[0].airline_name == "IndiGo"
    assert flights[0].price == 5200.0


def test_google_normalizer_places():
    mock_payload = {
        "places": [
            {
                "id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                "displayName": {"text": "Tarin High-Altitude Fish Farm"},
                "formattedAddress": "Ziro Valley, Arunachal Pradesh 791120",
                "location": {"latitude": 27.601, "longitude": 93.832},
                "rating": 4.6,
                "userRatingCount": 85,
                "types": ["park", "point_of_interest"],
                "photos": [
                    {
                        "name": "places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/photo_1",
                        "heightPx": 600,
                        "widthPx": 800,
                        "authorAttributions": [{"displayName": "Local Explorer"}],
                    }
                ],
            }
        ]
    }
    places = GooglePlacesNormalizer.normalize_places(mock_payload)
    assert len(places) == 1
    assert places[0].name == "Tarin High-Altitude Fish Farm"
    assert places[0].rating == 4.6
    assert len(places[0].photos) == 1
    assert places[0].photos[0].proxy_url == "/api/v1/travel/places/photos/places/ChIJN1t_tDeuEmsRUsoyG83frY4/photos/photo_1"


def test_google_normalizer_autocomplete():
    mock_payload = {
        "suggestions": [
            {
                "placePrediction": {
                    "placeId": "ChIJZiro123",
                    "text": {"text": "Ziro, Arunachal Pradesh, India"},
                    "structuredFormat": {
                        "mainText": {"text": "Ziro"},
                        "secondaryText": {"text": "Arunachal Pradesh, India"},
                    },
                    "types": ["locality", "political"],
                }
            }
        ]
    }
    items = GooglePlacesNormalizer.normalize_autocomplete(mock_payload)
    assert len(items) == 1
    assert items[0].place_id == "ChIJZiro123"
    assert items[0].primary_text == "Ziro"
    assert items[0].secondary_text == "Arunachal Pradesh, India"


# ---------------------------------------------------------------------------
# 3. Cache Manager Testing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_manager():
    cache = TravelCacheManager(default_ttl=1)
    key = cache.make_key("hotels", city="DEL", limit=5)
    key2 = cache.make_key("hotels", limit=5, city="DEL")
    assert key == key2, "Cache key generation must be deterministic regardless of param order"

    await cache.set(key, {"sample": "data"}, ttl_seconds=1)
    cached = await cache.get(key)
    assert cached == {"sample": "data"}

    # Test expiration
    await asyncio.sleep(1.1)
    expired = await cache.get(key)
    assert expired is None


# ---------------------------------------------------------------------------
# 4. Local Database Provider & Normalization Fallback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_local_db_provider(db_session: AsyncSession):
    # Seed minimal data
    country = Country(code="IN", name="India")
    db_session.add(country)
    await db_session.flush()

    state = State(country_id=country.id, name="Arunachal Pradesh", region="Northeast")
    db_session.add(state)
    await db_session.flush()

    city = City(state_id=state.id, name="Naharlagun", city_code="NHLN", latitude=27.1, longitude=93.69)
    db_session.add(city)
    await db_session.flush()

    dest = Destination(
        slug="ziro",
        name="Ziro Valley",
        state="Arunachal Pradesh",
        region="Northeast",
        category="Nature",
        best_season="Autumn",
        budget="₹₹",
        trust_score=95,
        description="Apatani cultural landscape",
        image_url="http://example.com/ziro.jpg",
        country_id=country.id,
        state_id=state.id,
        city_id=city.id,
        latitude=27.595,
        longitude=93.838,
    )
    db_session.add(dest)
    await db_session.flush()

    hotel = Hotel(
        destination_id=dest.id,
        city_id=city.id,
        name="Donyi Hango Apatani Homestay",
        stay_type="Homestay",
        address="Hong Village, Ziro",
        latitude=27.576,
        longitude=93.851,
        rating=4.9,
        price_level="₹₹",
    )
    db_session.add(hotel)

    attraction = Attraction(
        destination_id=dest.id,
        name="Hong Village",
        category="Cultural Village",
        description="Traditional stilt houses",
    )
    db_session.add(attraction)

    airport = Airport(
        city_id=city.id,
        name="Donyi Polo Airport",
        iata_code="HGI",
    )
    db_session.add(airport)
    await db_session.commit()

    # Create LocalDatabaseProvider with mock session_factory
    class MockSessionFactory:
        def __call__(self):
            return self
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, *args):
            pass

    local_provider = LocalDatabaseProvider(session_factory=MockSessionFactory())

    hotels = await local_provider.search_hotels(city_code="NHLN")
    assert len(hotels) >= 1
    assert hotels[0].name == "Donyi Hango Apatani Homestay"
    assert hotels[0].provider == "local_db"

    airports = await local_provider.search_airports(keyword="HGI")
    assert len(airports) >= 1
    assert airports[0].iata_code == "HGI"

    places = await local_provider.search_places(query="Hong")
    assert len(places) >= 1
    assert places[0].name == "Hong Village"


# ---------------------------------------------------------------------------
# 5. Travel Provider Service Fallback & Caching
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_travel_provider_service_fallback(db_session: AsyncSession):
    # Provider service when AirLabs/Google are unconfigured
    unconfigured_airlabs = AirLabsProvider(api_key="")
    unconfigured_google = GooglePlacesProvider(api_key="")

    class MockSessionFactory:
        def __call__(self):
            return self
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, *args):
            pass

    local_provider = LocalDatabaseProvider(session_factory=MockSessionFactory())

    service = TravelProviderService(
        airlabs_provider=unconfigured_airlabs,
        google_provider=unconfigured_google,
        local_db_provider=local_provider,
    )

    # Hotels should fall back to Local DB cleanly without errors
    hotels = await service.get_hotels(city_code="NHLN")
    assert isinstance(hotels, list)

    # Places should fall back to Local DB cleanly without errors
    places = await service.get_places(query="Ziro")
    assert isinstance(places, list)


# ---------------------------------------------------------------------------
# 6. API Endpoints Testing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_provider_status(client: AsyncClient):
    resp = await client.get("/api/v1/travel/providers/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    # AirLabs replaced Amadeus (decommissioned July 2026)
    assert "airlabs" in data["providers"] or "amadeus" in data["providers"]  # accept either during migration
    assert "google_places" in data["providers"]
    assert "local_db" in data["providers"]
    assert data["providers"]["local_db"]["configured"] is True


@pytest.mark.asyncio
async def test_api_places_search(client: AsyncClient):
    resp = await client.get("/api/v1/travel/places/search", params={"query": "Valley"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_hotels_search_validation(client: AsyncClient):
    # Missing required query parameters should yield 400
    resp = await client.get("/api/v1/travel/hotels/search")
    assert resp.status_code == 400
