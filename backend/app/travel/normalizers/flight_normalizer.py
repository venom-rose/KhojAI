"""Flight offer normalizer supporting Amadeus and AirLabs."""

from typing import Any, Dict, List
from backend.app.travel.schemas.internal import TravelFlight, TravelFlightSegment


class FlightNormalizer:
    """Transforms raw flight responses from Amadeus and AirLabs into TravelFlight schemas."""

    @staticmethod
    def normalize_amadeus(offer: Dict[str, Any]) -> TravelFlight:
        """Normalize Amadeus Flight Offers Search v2 response."""
        price_data = offer.get("price", {})
        itineraries = offer.get("itineraries", [])
        segments_list: List[TravelFlightSegment] = []

        total_duration = "N/A"
        dep_airport = "DEL"
        arr_airport = "GAU"
        dep_time = ""
        arr_time = ""
        carrier = "6E"
        flight_num = ""

        if itineraries:
            first_itin = itineraries[0]
            total_duration = first_itin.get("duration", "").replace("PT", "").lower()
            amadeus_segs = first_itin.get("segments", [])
            for seg in amadeus_segs:
                dep = seg.get("departure", {})
                arr = seg.get("arrival", {})
                segments_list.append(
                    TravelFlightSegment(
                        departure_airport=dep.get("iataCode", ""),
                        arrival_airport=arr.get("iataCode", ""),
                        departure_time=dep.get("at", ""),
                        arrival_time=arr.get("at", ""),
                        carrier_code=seg.get("carrierCode", ""),
                        flight_number=f"{seg.get('carrierCode', '')}-{seg.get('number', '')}",
                        duration=seg.get("duration", "").replace("PT", "").lower(),
                    )
                )
            if segments_list:
                dep_airport = segments_list[0].departure_airport
                arr_airport = segments_list[-1].arrival_airport
                dep_time = segments_list[0].departure_time
                arr_time = segments_list[-1].arrival_time
                carrier = segments_list[0].carrier_code
                flight_num = segments_list[0].flight_number

        try:
            total_price = float(price_data.get("total", 0.0))
        except (ValueError, TypeError):
            total_price = 0.0

        airline_names = {
            "6E": "IndiGo",
            "AI": "Air India",
            "UK": "Vistara",
            "SG": "SpiceJet",
            "QP": "Akasa Air",
        }

        return TravelFlight(
            offer_id=str(offer.get("id", "offer-amadeus")),
            airline_code=carrier,
            airline_name=airline_names.get(carrier, carrier),
            departure_airport=dep_airport,
            arrival_airport=arr_airport,
            departure_time=dep_time,
            arrival_time=arr_time,
            duration=total_duration,
            stops=max(0, len(segments_list) - 1),
            price=total_price,
            currency=price_data.get("currency", "INR"),
            segments=segments_list,
            provider="amadeus",
        )

    @staticmethod
    def normalize_airlabs(flight: Dict[str, Any]) -> TravelFlight:
        """Normalize AirLabs schedule or flight item."""
        airline_code = flight.get("airline_iata") or "6E"
        flight_num = flight.get("flight_iata") or flight.get("flight_number") or ""
        dep_code = flight.get("dep_iata") or ""
        arr_code = flight.get("arr_iata") or ""
        dep_time = flight.get("dep_time") or flight.get("dep_estimated") or ""
        arr_time = flight.get("arr_time") or flight.get("arr_estimated") or ""
        duration = flight.get("duration") or 150

        if isinstance(duration, (int, float)):
            hours = int(duration // 60)
            mins = int(duration % 60)
            dur_str = f"{hours}h {mins}m"
        else:
            dur_str = str(duration)

        segment = TravelFlightSegment(
            departure_airport=dep_code,
            arrival_airport=arr_code,
            departure_time=str(dep_time),
            arrival_time=str(arr_time),
            carrier_code=airline_code,
            flight_number=str(flight_num),
            duration=dur_str,
        )

        return TravelFlight(
            offer_id=f"al-{flight_num}-{dep_code}-{arr_code}",
            airline_code=airline_code,
            airline_name=flight.get("airline_name") or airline_code,
            departure_airport=dep_code,
            arrival_airport=arr_code,
            departure_time=str(dep_time),
            arrival_time=str(arr_time),
            duration=dur_str,
            stops=0,
            price=float(flight.get("price", 4500.0)),
            currency="INR",
            segments=[segment],
            provider="airlabs",
        )
