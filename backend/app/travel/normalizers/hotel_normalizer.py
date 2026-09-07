"""Hotel entity normalizer supporting Amadeus, Google Places, Geoapify, and Local DB."""

from typing import Any, Dict, List, Optional
from backend.app.travel.schemas.internal import TravelHotel


class HotelNormalizer:
    """Normalizes hotel payloads from various providers into TravelHotel schemas."""

    @staticmethod
    def normalize_amadeus(item: Dict[str, Any]) -> TravelHotel:
        """Normalize Amadeus hotel payload."""
        hotel_data = item.get("hotel", item)
        geocode = hotel_data.get("geoCode", {})
        address = hotel_data.get("address", {})

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

        price_tier = "₹₹"
        if price:
            if price < 2000:
                price_tier = "₹"
            elif price > 6000:
                price_tier = "₹₹₹"

        address_lines = address.get("lines", [])
        full_address = ", ".join(address_lines) if address_lines else None
        if not full_address and address.get("cityName"):
            full_address = f"{address.get('cityName')}, {address.get('countryCode', '')}".strip(", ")

        return TravelHotel(
            name=hotel_data.get("name") or "Hotel",
            hotel_id=hotel_data.get("hotelId") or str(item.get("id", "")),
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
            metadata={"source": "amadeus_self_service"},
        )

    @staticmethod
    def normalize_geoapify(feature: Dict[str, Any]) -> TravelHotel:
        """Normalize Geoapify accommodation / hotel feature."""
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [None, None])
        lon = coords[0] if len(coords) > 0 else props.get("lon")
        lat = coords[1] if len(coords) > 1 else props.get("lat")

        name = props.get("name") or props.get("address_line1") or "Boutique Stay"
        address = props.get("formatted") or props.get("address_line2") or ""

        return TravelHotel(
            name=name,
            hotel_id=props.get("place_id") or props.get("osm_id"),
            latitude=lat,
            longitude=lon,
            address=address,
            city_name=props.get("city"),
            country_code=props.get("country_code", "").upper(),
            rating=4.2,
            price_tier="₹₹",
            provider="geoapify",
            provider_id=props.get("place_id"),
            metadata={"categories": props.get("categories", [])},
        )

    @staticmethod
    def normalize_local(item: Any) -> TravelHotel:
        """Normalize a local database Hotel model or dictionary."""
        if isinstance(item, dict):
            return TravelHotel(
                name=item["name"],
                hotel_id=str(item.get("id", "")),
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                address=item.get("address"),
                city_name=item.get("city_name"),
                rating=item.get("rating", 4.5),
                price_tier=item.get("price_level", "₹₹"),
                amenities=item.get("amenities", []),
                provider="local_db",
                provider_id=str(item.get("id", "")),
                metadata={"stay_type": item.get("stay_type", "Homestay")},
            )
        return TravelHotel(
            name=item.name,
            hotel_id=str(item.id),
            latitude=item.latitude,
            longitude=item.longitude,
            address=item.address,
            city_name=getattr(item.city, "name", None) if hasattr(item, "city") and item.city else None,
            rating=getattr(item, "rating", 4.5),
            price_tier=getattr(item, "price_level", "₹₹"),
            amenities=getattr(item, "amenities", []),
            provider="local_db",
            provider_id=str(item.id),
            metadata={"stay_type": getattr(item, "stay_type", "Homestay")},
        )
