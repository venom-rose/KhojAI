"""Travel data providers package exporting adapters."""

# Active providers
from backend.app.travel.providers.airlabs_provider import AirLabsProvider
from backend.app.travel.providers.base import TravelDataProvider
from backend.app.travel.providers.google_places_provider import GooglePlacesProvider
from backend.app.travel.providers.local_db_provider import LocalDatabaseProvider
from backend.app.travel.providers.opentripmap_provider import OpenTripMapProvider

# Deprecated — Amadeus Self-Service was decommissioned July 17, 2026.
# Kept for import compatibility only. Do not use in new code.
from backend.app.travel.providers.amadeus_provider import AmadeusProvider  # noqa: F401

__all__ = [
    "TravelDataProvider",
    "AirLabsProvider",
    "OpenTripMapProvider",
    "GooglePlacesProvider",
    "LocalDatabaseProvider",
    "AmadeusProvider",  # deprecated
]
