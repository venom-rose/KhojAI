"""Unit and Integration Tests for KHOJAI Travel API Architecture & Providers."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.destination import Destination
from backend.app.travel.models.geo import City, Country, State
from backend.app.travel.models.poi import Activity, Attraction, Hotel
from backend.app.travel.normalizers import (
    DestinationNormalizer,
    HotelNormalizer,
    PlaceNormalizer,
    FlightNormalizer,
    ActivityNormalizer,
    AirportNormalizer,
)
from backend.app.travel.providers.amadeus_provider import AmadeusProvider
from backend.app.travel.providers.geoapify_provider import GeoapifyProvider
from backend.app.travel.providers.nominatim_provider import NominatimProvider
from backend.app.travel.providers.local_db_provider import LocalDatabaseProvider
from backend.app.travel.providers.opentripmap_provider import OpenTripMapProvider
from backend.app.travel.services import (
    DestinationService,
    HotelService,
    FlightService,
    ActivityService,
    PlaceService,
    TravelSearchService,
    TravelProviderService,
)
from backend.app.travel.schemas.internal import TravelDestination, TravelPlace


# ---------------------------------------------------------------------------
# 1. Normalizers Tests
# ---------------------------------------------------------------------------

def test_destination_normalizer():
    # From dict
    dict_data = {
        "name": "Ziro Valley",
        "slug": "ziro-valley",
        "state": "Arunachal Pradesh",
        "category": "nature",
        "latitude": 27.59,
        "longitude": 93.83,
        "tags": "peace,tribal,culture",
    }
    dest = DestinationNormalizer.from_dict(dict_data)
    assert isinstance(dest, TravelDestination)
    assert dest.slug == "ziro-valley"
    assert "tribal" in dest.tags
    assert dest.provider == "local_db"


def test_geoapify_normalizer():
    sample_feature = {
        "properties": {
            "name": "Tawang Monastery",
            "place_id": "geo_12345",
            "formatted": "Tawang, Arunachal Pradesh, India",
            "lat": 27.586,
            "lon": 91.865,
            "categories": ["tourism.sights", "heritage"],
            "contact": {"phone": "+91 3794 222"},
            "website": "http://tawangmonastery.com",
        },
        "geometry": {
            "coordinates": [91.865, 27.586]
        }
    }
    place = PlaceNormalizer.normalize_geoapify(sample_feature)
    assert isinstance(place, TravelPlace)
    assert place.name == "Tawang Monastery"
    assert place.place_id == "geo_12345"
    assert place.latitude == 27.586
    assert place.longitude == 91.865
    assert place.provider == "geoapify"


# ---------------------------------------------------------------------------
# 2. Providers Unit Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_geoapify_provider():
    provider = GeoapifyProvider(api_key="test_geo_key")
    assert provider.is_configured is True

    fake_response = {
        "features": [
            {
                "properties": {
                    "name": "Sangti Valley",
                    "place_id": "geo_sangti_1",
                    "formatted": "Dirang, Arunachal Pradesh",
                    "lat": 27.35,
                    "lon": 92.23,
                    "categories": ["tourism.sights"],
                },
                "geometry": {"coordinates": [92.23, 27.35]}
            }
        ]
    }

    with patch.object(provider, "_get", new=AsyncMock(return_value=fake_response)):
        places = await provider.search_places("Sangti")
        assert len(places) == 1
        assert places[0].name == "Sangti Valley"
        assert places[0].provider == "geoapify"


@pytest.mark.asyncio
async def test_nominatim_provider():
    provider = NominatimProvider(user_agent="KHOJAI-Test/1.0 (test@khojai.com)")
    assert provider.is_configured is True

    fake_search_res = [
        {
            "name": "Dambuk",
            "place_id": 999888,
            "display_name": "Dambuk, Lower Dibang Valley, Arunachal Pradesh, India",
            "lat": "28.21",
            "lon": "95.56",
            "category": "boundary",
            "type": "administrative",
        }
    ]

    with patch.object(provider, "_rate_limited_get", new=AsyncMock(return_value=fake_search_res)):
        results = await provider.search_places("Dambuk")
        assert len(results) == 1
        assert results[0].name == "Dambuk"
        assert results[0].latitude == 28.21
        assert results[0].provider == "nominatim"


@pytest.mark.asyncio
async def test_amadeus_provider_configuration():
    unconfigured = AmadeusProvider(client_id="", client_secret="")
    assert unconfigured.is_configured is False
    hotels = await unconfigured.search_hotels(city_code="DEL")
    assert hotels == []

    configured = AmadeusProvider(client_id="mock_id", client_secret="mock_sec")
    assert configured.is_configured is True


# ---------------------------------------------------------------------------
# 3. Services Unit Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_destination_service(db_session: AsyncSession):
    # Seed destination
    dest = Destination(
        slug="mawsynram",
        name="Mawsynram",
        state="Meghalaya",
        region="Northeast",
        category="Nature",
        best_season="Monsoon",
        budget="₹₹",
        image_url="https://images.unsplash.com/mawsynram.jpg",
        description="Wettest inhabited place on Earth with living root bridges nearby",
        latitude=25.297,
        longitude=91.582,
        trust_score=92,
    )
    db_session.add(dest)
    await db_session.commit()

    class MockSessionFactory:
        def __call__(self):
            return db_session

    svc = DestinationService(session_factory=MockSessionFactory())
    dest_found = await svc.get_destination_by_slug("mawsynram")
    assert dest_found is not None
    assert dest_found.name == "Mawsynram"
    assert dest_found.state == "Meghalaya"

    searched = await svc.search_destinations(query="wettest")
    assert len(searched) >= 1
    assert any(d.slug == "mawsynram" for d in searched)


@pytest.mark.asyncio
async def test_travel_search_service():
    mock_dest = MagicMock()
    mock_dest.search_destinations = AsyncMock(return_value=[
        TravelDestination(slug="hampi", name="Hampi", provider="local_db")
    ])

    mock_places = MagicMock()
    mock_places.search_places = AsyncMock(return_value=[])

    mock_hotels = MagicMock()
    mock_hotels.search_hotels = AsyncMock(return_value=[])

    mock_activities = MagicMock()
    mock_activities.search_activities = AsyncMock(return_value=[])

    search_svc = TravelSearchService(
        destination_service=mock_dest,
        hotel_service=mock_hotels,
        activity_service=mock_activities,
        place_service=mock_places,
    )

    result = await search_svc.search_all("Hampi")
    assert result.query == "Hampi"
    assert len(result.destinations) == 1
    assert result.total_count == 1


# ---------------------------------------------------------------------------
# 4. API Endpoints Integration Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_root_travel_providers(client: AsyncClient):
    resp = await client.get("/api/travel/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert "providers" in data
    # Providers must include amadeus, google_places, opentripmap, geoapify, nominatim, local_database
    for prov in ["amadeus", "google_places", "opentripmap", "geoapify", "nominatim", "local_database"]:
        assert prov in data["providers"], f"Missing provider {prov}"


@pytest.mark.asyncio
async def test_api_travel_health(client: AsyncClient):
    resp = await client.get("/api/health/travel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "cache" in data
    assert "providers" in data


@pytest.mark.asyncio
async def test_api_destinations_search(client: AsyncClient):
    resp = await client.get("/api/v1/travel/destinations/search", params={"query": "Ziro"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_places_nearby(client: AsyncClient):
    resp = await client.get(
        "/api/v1/travel/places/nearby",
        params={"latitude": 27.59, "longitude": 93.83, "radius_meters": 5000},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_api_unified_search(client: AsyncClient):
    resp = await client.get("/api/v1/travel/search", params={"query": "Valley"})
    assert resp.status_code == 200
    data = resp.json()
    assert "destinations" in data
    assert "places" in data
    assert "hotels" in data
    assert "activities" in data
