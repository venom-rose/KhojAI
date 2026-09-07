"""Airport normalizer supporting Amadeus, AirLabs, and Local DB."""

from typing import Any, Dict
from backend.app.travel.schemas.internal import TravelAirport


class AirportNormalizer:
    """Transforms airport payloads into TravelAirport schemas."""

    @staticmethod
    def normalize_amadeus(loc: Dict[str, Any]) -> TravelAirport:
        """Normalize Amadeus Airport & City Search payload."""
        geo = loc.get("geoCode", {})
        addr = loc.get("address", {})
        distance = loc.get("distance", {})

        return TravelAirport(
            name=loc.get("name") or loc.get("detailedName") or "Airport",
            iata_code=loc.get("iataCode", ""),
            city_name=addr.get("cityName"),
            country_code=addr.get("countryCode"),
            latitude=geo.get("latitude"),
            longitude=geo.get("longitude"),
            distance_km=distance.get("value"),
            provider="amadeus",
        )

    @staticmethod
    def normalize_airlabs(airport: Dict[str, Any]) -> TravelAirport:
        """Normalize AirLabs airport item."""
        return TravelAirport(
            name=airport.get("name", ""),
            iata_code=airport.get("iata_code", ""),
            icao_code=airport.get("icao_code"),
            city_name=airport.get("city"),
            country_code=airport.get("country_code"),
            latitude=airport.get("lat"),
            longitude=airport.get("lng"),
            provider="airlabs",
        )

    @staticmethod
    def normalize_local(item: Any) -> TravelAirport:
        """Normalize local database Airport entity."""
        if isinstance(item, dict):
            return TravelAirport(
                name=item["name"],
                iata_code=item["iata_code"],
                icao_code=item.get("icao_code"),
                city_name=item.get("city_name"),
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                provider="local_db",
            )
        return TravelAirport(
            name=item.name,
            iata_code=item.iata_code,
            icao_code=item.icao_code,
            city_name=getattr(item.city, "name", None) if hasattr(item, "city") and item.city else None,
            latitude=item.latitude,
            longitude=item.longitude,
            provider="local_db",
        )
