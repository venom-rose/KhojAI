"""Normalizers converting raw Amadeus API responses into internal provider-independent schemas."""

from typing import Any, Dict, List, Optional
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelFlightSegment,
    TravelHotel,
)


class AmadeusNormalizer:
    """Transforms Amadeus response payloads into standard KHOJAI travel entities."""

    @staticmethod
    def normalize_hotels(payload: Dict[str, Any]) -> List[TravelHotel]:
        """Normalize hotel search by city/geocode or hotel offers."""
        items: List[TravelHotel] = []
        data = payload.get("data", [])
        if isinstance(data, dict):
            data = [data]

        for item in data:
            # Amadeus can return simple reference-data hotel or hotel-offers structure
            hotel_data = item.get("hotel", item)
            geocode = hotel_data.get("geoCode", {})
            address = hotel_data.get("address", {})

            # Extract price if available from offers
            offers = item.get("offers", [])
            price = None
            currency = "INR"
            booking_url = None
            if offers:
                first_offer = offers[0]
                price_obj = first_offer.get("price", {})
                try:
                    price = float(price_obj.get("total", 0.0))
                except (ValueError, TypeError):
                    price = None
                currency = price_obj.get("currency", "INR")
                booking_url = first_offer.get("self")

            # Determine price tier
            price_tier = "₹₹"
            if price:
                if price < 2000:
                    price_tier = "₹"
                elif price > 6000:
                    price_tier = "₹₹₹"

            # Parse address string
            address_lines = address.get("lines", [])
            full_address = ", ".join(address_lines) if address_lines else None
            if not full_address and address.get("cityName"):
                full_address = f"{address.get('cityName')}, {address.get('countryCode', '')}".strip(", ")

            items.append(
                TravelHotel(
                    name=hotel_data.get("name") or "Amadeus Partner Hotel",
                    hotel_id=hotel_data.get("hotelId") or item.get("id"),
                    chain_code=hotel_data.get("chainCode"),
                    latitude=geocode.get("latitude"),
                    longitude=geocode.get("longitude"),
                    address=full_address,
                    city_name=address.get("cityName"),
                    country_code=address.get("countryCode"),
                    rating=float(hotel_data.get("rating", 4.0)) if hotel_data.get("rating") else 4.2,
                    price_tier=price_tier,
                    price=price,
                    currency=currency,
                    amenities=hotel_data.get("amenities", []),
                    photo_urls=[],
                    provider="amadeus",
                    provider_id=hotel_data.get("hotelId"),
                    booking_url=booking_url,
                    metadata={"amadeus_dupe_id": hotel_data.get("dupeId")},
                )
            )
        return items

    @staticmethod
    def normalize_flights(payload: Dict[str, Any]) -> List[TravelFlight]:
        """Normalize Amadeus flight-offers search results."""
        flights: List[TravelFlight] = []
        data = payload.get("data", [])
        dictionaries = payload.get("dictionaries", {})
        carriers = dictionaries.get("carriers", {})

        for item in data:
            offer_id = item.get("id", "")
            price_data = item.get("price", {})
            try:
                total_price = float(price_data.get("total", 0.0))
            except (ValueError, TypeError):
                total_price = 0.0
            currency = price_data.get("currency", "INR")

            itineraries = item.get("itineraries", [])
            if not itineraries:
                continue

            primary_itin = itineraries[0]
            itin_duration = primary_itin.get("duration", "").replace("PT", "").lower()
            segments_raw = primary_itin.get("segments", [])

            segments: List[TravelFlightSegment] = []
            for s in segments_raw:
                dep = s.get("departure", {})
                arr = s.get("arrival", {})
                carrier = s.get("carrierCode", "")
                segments.append(
                    TravelFlightSegment(
                        departure_airport=dep.get("iataCode", ""),
                        arrival_airport=arr.get("iataCode", ""),
                        departure_time=dep.get("at", ""),
                        arrival_time=arr.get("at", ""),
                        carrier_code=carrier,
                        flight_number=f"{carrier}{s.get('number', '')}",
                        duration=s.get("duration", "").replace("PT", "").lower(),
                    )
                )

            if not segments:
                continue

            first_seg = segments[0]
            last_seg = segments[-1]
            airline_code = first_seg.carrier_code
            airline_name = carriers.get(airline_code, airline_code)

            flights.append(
                TravelFlight(
                    offer_id=offer_id,
                    airline_code=airline_code,
                    airline_name=airline_name,
                    departure_airport=first_seg.departure_airport,
                    arrival_airport=last_seg.arrival_airport,
                    departure_time=first_seg.departure_time,
                    arrival_time=last_seg.arrival_time,
                    duration=itin_duration or first_seg.duration or "3h",
                    stops=len(segments) - 1,
                    price=total_price,
                    currency=currency,
                    segments=segments,
                    provider="amadeus",
                )
            )
        return flights

    @staticmethod
    def normalize_activities(payload: Dict[str, Any]) -> List[TravelActivity]:
        """Normalize Amadeus tours and activities results."""
        activities: List[TravelActivity] = []
        data = payload.get("data", [])

        for item in data:
            geocode = item.get("geoCode", {})
            price_data = item.get("price", {})
            amount = None
            if "amount" in price_data:
                try:
                    amount = float(price_data["amount"])
                except (ValueError, TypeError):
                    amount = None

            activities.append(
                TravelActivity(
                    title=item.get("name") or "Local Experience",
                    description=item.get("shortDescription") or item.get("description"),
                    activity_type=item.get("type", "Activity"),
                    duration=item.get("duration"),
                    price=amount,
                    currency=price_data.get("currencyCode", "INR"),
                    latitude=geocode.get("latitude"),
                    longitude=geocode.get("longitude"),
                    rating=float(item.get("rating", 4.5)) if item.get("rating") else None,
                    pictures=item.get("pictures", []),
                    booking_url=item.get("bookingLink"),
                    provider="amadeus",
                    provider_id=item.get("id"),
                )
            )
        return activities

    @staticmethod
    def normalize_airports(payload: Dict[str, Any]) -> List[TravelAirport]:
        """Normalize Amadeus location search (airports/cities)."""
        airports: List[TravelAirport] = []
        data = payload.get("data", [])

        for item in data:
            geocode = item.get("geoCode", {})
            address = item.get("address", {})
            airports.append(
                TravelAirport(
                    name=item.get("name") or item.get("detailedName") or "Airport",
                    iata_code=item.get("iataCode", ""),
                    city_name=address.get("cityName"),
                    country_code=address.get("countryCode"),
                    latitude=geocode.get("latitude"),
                    longitude=geocode.get("longitude"),
                    distance_km=item.get("distance", {}).get("value") if isinstance(item.get("distance"), dict) else None,
                    provider="amadeus",
                )
            )
        return airports
