"""Travel normalizer package exporting converters."""

# Active normalizers
from backend.app.travel.normalizers.airlabs_normalizer import AirLabsNormalizer
from backend.app.travel.normalizers.google_normalizer import GooglePlacesNormalizer
from backend.app.travel.normalizers.local_normalizer import LocalDatabaseNormalizer
from backend.app.travel.normalizers.opentripmap_normalizer import OpenTripMapNormalizer

# Deprecated — Amadeus Self-Service was decommissioned July 17, 2026.
from backend.app.travel.normalizers.amadeus_normalizer import AmadeusNormalizer  # noqa: F401

__all__ = [
    "AirLabsNormalizer",
    "OpenTripMapNormalizer",
    "GooglePlacesNormalizer",
    "LocalDatabaseNormalizer",
    "AmadeusNormalizer",  # deprecated
]
