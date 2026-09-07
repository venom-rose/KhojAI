"""Travel Provider API endpoints for KHOJAI (Amadeus, Google Places, OpenTripMap, Geoapify, Nominatim, and Local DB)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import get_db
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelDestination,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)
from backend.app.travel.services.destination_service import DestinationService
from backend.app.travel.services.travel_provider_service import TravelProviderService
from backend.app.travel.services.travel_search_service import TravelSearchService, UnifiedTravelSearchResult

router = APIRouter(prefix="/travel", tags=["Travel Providers & External APIs"])

# Service singletons
travel_service = TravelProviderService()
destination_service = DestinationService()
travel_search_service = TravelSearchService()


# --- Providers Status ---
@router.get(
    "/providers",
    summary="Travel Provider Status",
    description="Inspect configured travel provider adapters and capabilities without exposing credentials.",
)
@router.get(
    "/providers/status",
    summary="Travel Provider Status (Legacy alias)",
    description="Inspect configured travel provider adapters and capabilities.",
)
async def get_provider_status():
    return {
        "status": "healthy",
        "providers": travel_service.get_providers_status(),
        "resilience": {
            "rate_limit_handling": "enabled",
            "provider_failure_fallback": "local_db",
            "circuit_breaker": "active",
        },
    }


# --- Unified Multi-Domain Search ---
@router.get(
    "/search",
    response_model=UnifiedTravelSearchResult,
    summary="Unified Multi-Domain Travel Search",
    description="Search across destinations, places, hotels, and activities concurrently.",
)
async def unified_search(
    query: str = Query(..., min_length=1, description="Search query string (e.g. 'Goa', 'Spiti')"),
    latitude: Optional[float] = Query(None, description="Optional WGS84 latitude"),
    longitude: Optional[float] = Query(None, description="Optional WGS84 longitude"),
    limit: int = Query(5, ge=1, le=20, description="Max results per domain"),
):
    return await travel_search_service.search_all(
        query=query,
        latitude=latitude,
        longitude=longitude,
        limit_per_category=limit,
    )


# --- Destinations ---
@router.get(
    "/destinations/search",
    response_model=List[TravelDestination],
    summary="Search Destinations",
    description="Search curated Indian destinations by name, state, or category.",
)
async def search_destinations(
    query: Optional[str] = Query(None, description="Destination name or description keyword"),
    state: Optional[str] = Query(None, description="State or Union Territory name"),
    category: Optional[str] = Query(None, description="Destination category (e.g. 'spiritual', 'nature')"),
    limit: int = Query(20, ge=1, le=100),
    force_refresh: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    return await destination_service.search_destinations(
        query=query,
        state=state,
        category=category,
        limit=limit,
        force_refresh=force_refresh,
        db=db,
    )


@router.get(
    "/destinations/{slug}",
    response_model=TravelDestination,
    summary="Get Destination by Slug",
    description="Retrieve full destination details and metadata by slug identifier.",
)
async def get_destination_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    dest = await destination_service.get_destination_by_slug(slug, db=db)
    if not dest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination with slug '{slug}' not found.",
        )
    return dest


@router.get(
    "/destinations/{slug}/experiences",
    response_model=List[TravelActivity],
    summary="Destination Experiences & Activities",
    description="Retrieve curated cultural, nature, and adventure activities for a destination.",
)
async def get_destination_experiences(
    slug: str,
    limit: int = Query(15, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    return await destination_service.get_destination_experiences(slug=slug, limit=limit, db=db)


# --- Hotels ---
@router.get(
    "/hotels/search",
    response_model=List[TravelHotel],
    summary="Search Hotels",
    description="Search hotels via Amadeus API (with Google Places, Geoapify, and Local DB fallback).",
)
async def search_hotels(
    city_code: Optional[str] = Query(None, description="3-letter IATA city code (e.g. 'DEL', 'GAU', 'IXL')"),
    latitude: Optional[float] = Query(None, description="WGS84 latitude"),
    longitude: Optional[float] = Query(None, description="WGS84 longitude"),
    radius_km: int = Query(20, ge=1, le=100, description="Search radius in kilometers"),
    limit: int = Query(15, ge=1, le=50, description="Max results"),
    force_refresh: bool = Query(False, description="Bypass cache"),
):
    if not city_code and (latitude is None or longitude is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either city_code or latitude and longitude must be provided.",
        )
    return await travel_service.get_hotels(
        city_code=city_code,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit,
        force_refresh=force_refresh,
    )


# --- Flights ---
@router.get(
    "/flights/search",
    response_model=List[TravelFlight],
    summary="Search Flights",
    description="Search live flight offers via Amadeus API between airport/city codes.",
)
async def search_flights(
    origin: str = Query(..., description="Origin 3-letter IATA code (e.g. 'DEL')"),
    destination: str = Query(..., description="Destination 3-letter IATA code (e.g. 'GAU')"),
    departure_date: str = Query(..., description="Departure date in YYYY-MM-DD format"),
    adults: int = Query(1, ge=1, le=9, description="Number of adult travelers"),
    return_date: Optional[str] = Query(None, description="Optional return date in YYYY-MM-DD format"),
    limit: int = Query(10, ge=1, le=50),
    force_refresh: bool = Query(False),
):
    return await travel_service.get_flights(
        origin_code=origin,
        destination_code=destination,
        departure_date=departure_date,
        adults=adults,
        return_date=return_date,
        limit=limit,
        force_refresh=force_refresh,
    )


# --- Activities ---
@router.get(
    "/activities/search",
    response_model=List[TravelActivity],
    summary="Search Destination Experiences & Activities",
    description="Search tours, cultural workshops, and activities by geographic coordinates.",
)
async def search_activities(
    latitude: float = Query(..., description="WGS84 latitude"),
    longitude: float = Query(..., description="WGS84 longitude"),
    radius_km: int = Query(25, ge=1, le=100),
    limit: int = Query(15, ge=1, le=50),
    force_refresh: bool = Query(False),
):
    return await travel_service.get_activities(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        limit=limit,
        force_refresh=force_refresh,
    )


# --- Airports ---
@router.get(
    "/airports/search",
    response_model=List[TravelAirport],
    summary="Search Airports",
    description="Search airports by name keyword or nearest coordinates.",
)
async def search_airports(
    keyword: Optional[str] = Query(None, description="Search keyword name or code"),
    latitude: Optional[float] = Query(None, description="WGS84 latitude"),
    longitude: Optional[float] = Query(None, description="WGS84 longitude"),
    limit: int = Query(10, ge=1, le=50),
    force_refresh: bool = Query(False),
):
    return await travel_service.get_airports(
        keyword=keyword,
        latitude=latitude,
        longitude=longitude,
        limit=limit,
        force_refresh=force_refresh,
    )


# --- Places & POIs ---
@router.get(
    "/places/search",
    response_model=List[TravelPlace],
    summary="Search Places & POIs",
    description="Search points of interest via Google Places API (New) with Local DB fallback.",
)
async def search_places(
    query: str = Query(..., min_length=1, description="Text query or place category"),
    latitude: Optional[float] = Query(None, description="WGS84 latitude bias"),
    longitude: Optional[float] = Query(None, description="WGS84 longitude bias"),
    radius_meters: int = Query(10000, ge=500, le=50000),
    limit: int = Query(15, ge=1, le=20),
    force_refresh: bool = Query(False),
):
    return await travel_service.get_places(
        query=query,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        limit=limit,
        force_refresh=force_refresh,
    )


@router.get(
    "/places/nearby",
    response_model=List[TravelPlace],
    summary="Search Nearby Places",
    description="Search places around coordinates with optional category filters.",
)
async def search_nearby_places(
    latitude: float = Query(..., description="WGS84 latitude"),
    longitude: float = Query(..., description="WGS84 longitude"),
    radius_meters: int = Query(5000, ge=100, le=50000),
    type: Optional[str] = Query(None, description="Place type category"),
    limit: int = Query(15, ge=1, le=50),
    force_refresh: bool = Query(False),
):
    types = [type] if type else None
    return await travel_service.get_places(
        query="",
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
        included_types=types,
        limit=limit,
        force_refresh=force_refresh,
    )


@router.get(
    "/places/details",
    response_model=TravelPlace,
    summary="Get Place Details",
    description="Retrieve detailed place metadata including reviews, hours, and contacts.",
)
async def get_place_details(
    place_id: str = Query(..., description="Google Place ID or Local entity UUID"),
    force_refresh: bool = Query(False),
):
    place = await travel_service.get_place_details(place_id=place_id, force_refresh=force_refresh)
    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Place '{place_id}' not found.",
        )
    return place


@router.get(
    "/places/autocomplete",
    response_model=List[TravelPlaceAutocompleteItem],
    summary="Place Search Autocomplete",
    description="Predictive destination and POI search autocomplete suggestions.",
)
async def autocomplete_places(
    input_text: str = Query(..., min_length=1, description="User input characters"),
    latitude: Optional[float] = Query(None, description="Location bias latitude"),
    longitude: Optional[float] = Query(None, description="Location bias longitude"),
    radius_meters: int = Query(50000, ge=1000, le=100000),
):
    return await travel_service.autocomplete_places(
        input_text=input_text,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius_meters,
    )


@router.get(
    "/places/photos/{photo_name:path}",
    summary="Secure Photo Proxy",
    description="Stream photos securely from Google Places without exposing API keys to the browser.",
)
async def proxy_place_photo(photo_name: str):
    result = await travel_service.fetch_place_photo(photo_name)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo unavailable or not found.",
        )
    content, content_type = result
    return Response(
        content=content,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
