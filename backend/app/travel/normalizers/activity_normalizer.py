"""Activity and experiential tour normalizer for Amadeus, OpenTripMap, and Local DB."""

from typing import Any, Dict, List
from backend.app.travel.schemas.internal import TravelActivity


class ActivityNormalizer:
    """Transforms experiential tour payloads into TravelActivity schemas."""

    @staticmethod
    def normalize_amadeus(item: Dict[str, Any]) -> TravelActivity:
        """Normalize Amadeus Tours and Activities API payload."""
        geo = item.get("geoCode", {})
        price_obj = item.get("price", {})
        try:
            price_val = float(price_obj.get("amount", 0.0))
        except (ValueError, TypeError):
            price_val = None

        return TravelActivity(
            title=item.get("name") or "Local Experience",
            description=item.get("shortDescription"),
            activity_type=item.get("type", "Activity"),
            price=price_val,
            currency=price_obj.get("currencyCode", "INR"),
            latitude=geo.get("latitude"),
            longitude=geo.get("longitude"),
            rating=float(item.get("rating", 4.5)) if item.get("rating") else 4.5,
            pictures=item.get("pictures", []),
            booking_url=item.get("bookingLink"),
            provider="amadeus",
            provider_id=item.get("id"),
        )

    @staticmethod
    def normalize_opentripmap(item: Dict[str, Any]) -> TravelActivity:
        """Normalize OpenTripMap point into a cultural/outdoor activity."""
        props = item.get("properties", {})
        geom = item.get("geometry", {})
        coords = geom.get("coordinates", [None, None])

        name = props.get("name") or item.get("name") or "Cultural Exploration"
        kinds = props.get("kinds", "") or item.get("kinds", "")
        kinds_list = kinds.split(",") if kinds else []
        act_type = "Heritage Trail" if "historic" in kinds else "Nature Discovery"

        return TravelActivity(
            title=f"Explore {name}",
            description=f"Self-guided experience of {name}. Featured categories: {', '.join(kinds_list[:3])}.",
            activity_type=act_type,
            price=0.0,
            currency="INR",
            latitude=coords[1] if len(coords) > 1 else item.get("point", {}).get("lat"),
            longitude=coords[0] if len(coords) > 0 else item.get("point", {}).get("lon"),
            rating=4.5,
            provider="opentripmap",
            provider_id=props.get("xid") or item.get("xid"),
        )

    @staticmethod
    def normalize_local(item: Any) -> TravelActivity:
        """Normalize local database Activity entity."""
        if isinstance(item, dict):
            return TravelActivity(
                title=item["title"],
                description=item.get("description"),
                activity_type=item.get("activity_type", "Workshop"),
                duration=f"{item.get('duration_hours', 2.5)} hours",
                price=500.0,
                currency="INR",
                provider="local_db",
                provider_id=str(item.get("id", "")),
            )
        return TravelActivity(
            title=item.title,
            description=item.description,
            activity_type=item.activity_type,
            duration=f"{item.duration_hours} hours",
            price=500.0,
            currency="INR",
            provider="local_db",
            provider_id=str(item.id),
        )
