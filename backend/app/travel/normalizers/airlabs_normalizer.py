"""Normalizers converting raw AirLabs API responses into internal KHOJAI schemas."""

from typing import Any, Dict, List
from backend.app.travel.schemas.internal import TravelAirport, TravelFlight, TravelFlightSegment


class AirLabsNormalizer:
    """Transforms AirLabs response payloads into standard KHOJAI travel entities."""

    @staticmethod
    def normalize_airports(payload: Dict[str, Any]) -> List[TravelAirport]:
        """Normalize AirLabs /airports response."""
        airports: List[TravelAirport] = []
        items = payload.get("response", [])
        if not isinstance(items, list):
            return airports

        for item in items:
            iata = item.get("iata_code") or ""
            if not iata:
                # Skip heliports and non-IATA aerodromes
                continue

            try:
                lat = float(item["lat"]) if item.get("lat") else None
                lon = float(item["lng"]) if item.get("lng") else None
            except (TypeError, ValueError):
                lat, lon = None, None

            airports.append(
                TravelAirport(
                    name=item.get("name") or item.get("city") or "Airport",
                    iata_code=iata.upper(),
                    icao_code=item.get("icao_code"),
                    city_name=item.get("city"),
                    country_code=item.get("country_code"),
                    latitude=lat,
                    longitude=lon,
                    distance_km=item.get("_distance_km"),  # injected by proximity filter
                    provider="airlabs",
                )
            )
        return airports

    @staticmethod
    def normalize_routes(
        payload: Dict[str, Any],
        origin_code: str,
        destination_code: str,
        departure_date: str,
    ) -> List[TravelFlight]:
        """Normalize AirLabs /routes response into flight schedule summaries.

        AirLabs routes are schedule-based (not real-time priced offers), so
        price is unavailable and set to 0.0 with currency 'INR'.
        """
        flights: List[TravelFlight] = []
        items = payload.get("response", [])
        if not isinstance(items, list):
            return flights

        for item in items:
            airline_iata = item.get("airline_iata", "")
            flight_number = item.get("flight_number") or ""
            full_number = f"{airline_iata}{flight_number}".strip()

            # Build departure/arrival time strings from schedule
            dep_time = item.get("dep_time") or "00:00"
            arr_time = item.get("arr_time") or "00:00"
            dep_datetime = f"{departure_date}T{dep_time}:00"
            arr_datetime = f"{departure_date}T{arr_time}:00"

            # Estimate duration from times if available
            duration = _estimate_duration(dep_time, arr_time)

            segment = TravelFlightSegment(
                departure_airport=origin_code,
                arrival_airport=destination_code,
                departure_time=dep_datetime,
                arrival_time=arr_datetime,
                carrier_code=airline_iata,
                flight_number=full_number,
                duration=duration,
            )

            flights.append(
                TravelFlight(
                    offer_id=f"airlabs-{full_number}-{departure_date}",
                    airline_code=airline_iata,
                    airline_name=item.get("airline_name") or airline_iata,
                    departure_airport=origin_code,
                    arrival_airport=destination_code,
                    departure_time=dep_datetime,
                    arrival_time=arr_datetime,
                    duration=duration,
                    stops=0,
                    price=0.0,  # AirLabs is schedule data only, not pricing
                    currency="INR",
                    segments=[segment],
                    provider="airlabs",
                    booking_url=None,
                )
            )
        return flights


def _estimate_duration(dep_time: str, arr_time: str) -> str:
    """Estimate HH:MM duration string from departure and arrival time strings."""
    try:
        dep_h, dep_m = map(int, dep_time.split(":"))
        arr_h, arr_m = map(int, arr_time.split(":"))
        total_dep = dep_h * 60 + dep_m
        total_arr = arr_h * 60 + arr_m
        diff = total_arr - total_dep
        if diff < 0:
            diff += 24 * 60  # overnight flight
        hours, mins = divmod(diff, 60)
        return f"{hours}h {mins:02d}m"
    except (ValueError, AttributeError):
        return "unknown"
