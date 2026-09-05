"""Travel Provider API endpoints for KHOJAI (Amadeus, Google Places, and Local DB)."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status

from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)
from backend.app.travel.services.travel_provider_service import TravelProviderService

router = APIRouter(prefix="/travel", tags=["Travel Providers & External APIs"])

# Service singleton
travel_service = TravelProviderService()


@router.get(
    "/hotels/search",
    response_model=List[TravelHotel],
    summary="Search Hotels",
    description="Search hotels via Amadeus API (with Local DB fallback) using city code or coordinates.",
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


@router.get(
    "/providers/status",
    summary="Travel Provider Status",
    description="Inspect configured travel provider adapters and cache status.",
)
async def get_provider_status():
    return {
        "providers": {
            "airlabs": {
                "name": "AirLabs Aviation Data API",
                "configured": travel_service.airlabs.is_configured,
                "capabilities": ["airports", "flight_routes", "flight_schedules"],
                "note": "Replaces Amadeus Self-Service (decommissioned July 17, 2026)",
            },
            "opentripmap": {
                "name": "OpenTripMap POI & Attractions API",
                "configured": travel_service.opentripmap.is_configured,
                "capabilities": ["activities", "attractions", "places_search", "autocomplete", "poi_details"],
            },
            "google_places": {
                "name": "Google Places API (New)",
                "configured": travel_service.google.is_configured,
                "capabilities": ["places_search", "autocomplete", "details", "photos", "reviews", "hotels"],
            },
            "local_db": {
                "name": "Local Database Provider (PostgreSQL / SQLite)",
                "configured": True,
                "capabilities": ["hotels", "places", "activities", "airports", "fallback"],
            },
        },
        "resilience": {
            "rate_limit_handling": "enabled",
            "provider_failure_fallback": "local_db",
            "timeout_seconds": travel_service.airlabs.timeout,
            "max_retries": travel_service.airlabs.max_retries,
        },
    }
