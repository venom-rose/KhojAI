"""Travel normalizer package exporting converters."""

# Provider-independent normalizers
from backend.app.travel.normalizers.hotel_normalizer import HotelNormalizer
from backend.app.travel.normalizers.place_normalizer import PlaceNormalizer
from backend.app.travel.normalizers.flight_normalizer import FlightNormalizer
from backend.app.travel.normalizers.activity_normalizer import ActivityNormalizer
from backend.app.travel.normalizers.airport_normalizer import AirportNormalizer
from backend.app.travel.normalizers.destination_normalizer import DestinationNormalizer

# Legacy normalizers for backward compatibility
from backend.app.travel.normalizers.airlabs_normalizer import AirLabsNormalizer
from backend.app.travel.normalizers.google_normalizer import GooglePlacesNormalizer
from backend.app.travel.normalizers.local_normalizer import LocalDatabaseNormalizer
from backend.app.travel.normalizers.opentripmap_normalizer import OpenTripMapNormalizer
from backend.app.travel.normalizers.amadeus_normalizer import AmadeusNormalizer  # noqa: F401

__all__ = [
    "HotelNormalizer",
    "PlaceNormalizer",
    "FlightNormalizer",
    "ActivityNormalizer",
    "AirportNormalizer",
    "DestinationNormalizer",
    "AirLabsNormalizer",
    "OpenTripMapNormalizer",
    "GooglePlacesNormalizer",
    "LocalDatabaseNormalizer",
    "AmadeusNormalizer",
]
