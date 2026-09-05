"""Normalizers converting raw OpenTripMap API responses into internal KHOJAI schemas."""

from typing import Any, Dict, List, Optional
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)

# Map OpenTripMap 'kinds' to human-readable activity type labels
KIND_LABEL_MAP: Dict[str, str] = {
    "historic": "Historic Site",
    "cultural": "Cultural Experience",
    "natural": "Nature & Outdoors",
    "religion": "Temple / Shrine",
    "architecture": "Architecture",
    "museums": "Museum",
    "theatres_and_entertainments": "Entertainment",
    "amusements": "Amusement",
    "sport": "Sport & Adventure",
    "national_parks": "National Park",
    "water": "Water Feature",
    "beaches_and_water_sports": "Beach",
    "fishing": "Fishing",
    "mountains": "Mountain",
    "tourist_object": "Tourist Attraction",
    "foods": "Food & Dining",
}


def _kind_to_label(kinds_str: str) -> str:
    """Convert comma-separated OpenTripMap kinds to the most specific label."""
    if not kinds_str:
        return "Attraction"
    for kind in kinds_str.split(","):
        label = KIND_LABEL_MAP.get(kind.strip().lower())
        if label:
            return label
    return "Attraction"


class OpenTripMapNormalizer:
    """Transforms OpenTripMap response payloads into standard KHOJAI travel entities."""

    @staticmethod
    def normalize_activities(data: Any) -> List[TravelActivity]:
        """Normalize /radius response (list of feature objects) into TravelActivity list."""
        activities: List[TravelActivity] = []

        if isinstance(data, dict):
            # GeoJSON FeatureCollection
            items = data.get("features", data.get("response", []))
        elif isinstance(data, list):
            items = data
        else:
            return activities

        for item in items:
            try:
                # Handle GeoJSON Feature wrapper
                if isinstance(item, dict) and item.get("type") == "Feature":
                    props = item.get("properties", {})
                    geom = item.get("geometry", {})
                    coords = geom.get("coordinates", [None, None])
                    lon = coords[0] if len(coords) > 0 else None
                    lat = coords[1] if len(coords) > 1 else None
                else:
                    props = item
                    lat = item.get("lat")
                    lon = item.get("lon")

                xid = props.get("xid") or props.get("id") or ""
                name = props.get("name") or props.get("title") or "Local Attraction"
                kinds = props.get("kinds", "tourist_object")
                activity_type = _kind_to_label(kinds)

                # OpenTripMap radius results don't include descriptions or prices
                # — those come from the /xid/:id detail endpoint
                activities.append(
                    TravelActivity(
                        title=name,
                        description=props.get("wikipedia_extracts", {}).get("text")
                        if isinstance(props.get("wikipedia_extracts"), dict)
                        else props.get("info", {}).get("descr") if isinstance(props.get("info"), dict) else None,
                        activity_type=activity_type,
                        duration=None,
                        price=None,
                        currency="INR",
                        latitude=float(lat) if lat is not None else None,
                        longitude=float(lon) if lon is not None else None,
                        rating=props.get("rate"),
                        pictures=[],
                        booking_url=None,
                        provider="opentripmap",
                        provider_id=xid,
                    )
                )
            except Exception:
                continue

        return activities

    @staticmethod
    def normalize_places(data: Any) -> List[TravelPlace]:
        """Normalize OpenTripMap search results into TravelPlace list."""
        places: List[TravelPlace] = []

        if isinstance(data, dict):
            items = data.get("features", data.get("response", []))
        elif isinstance(data, list):
            items = data
        else:
            return places

        for item in items:
            try:
                if isinstance(item, dict) and item.get("type") == "Feature":
                    props = item.get("properties", {})
                    geom = item.get("geometry", {})
                    coords = geom.get("coordinates", [None, None])
                    lon = coords[0] if len(coords) > 0 else None
                    lat = coords[1] if len(coords) > 1 else None
                else:
                    props = item
                    lat = item.get("lat")
                    lon = item.get("lon")

                xid = props.get("xid") or ""
                name = props.get("name") or "Place"
                kinds = props.get("kinds", "")
                types_list = [k.strip() for k in kinds.split(",") if k.strip()]

                places.append(
                    TravelPlace(
                        name=name,
                        place_id=xid,
                        formatted_address=props.get("address", {}).get("formatted")
                        if isinstance(props.get("address"), dict)
                        else None,
                        latitude=float(lat) if lat is not None else None,
                        longitude=float(lon) if lon is not None else None,
                        types=types_list,
                        rating=props.get("rate"),
                        provider="opentripmap",
                        provider_id=xid,
                        metadata={"kinds": kinds},
                    )
                )
            except Exception:
                continue

        return places

    @staticmethod
    def normalize_place_detail(data: Dict[str, Any]) -> Optional[TravelPlace]:
        """Normalize a single /xid/:id detail response."""
        if not data or not data.get("xid"):
            return None

        try:
            point = data.get("point", {})
            lat = point.get("lat")
            lon = point.get("lon")

            address = data.get("address", {})
            address_parts = [
                address.get("road"),
                address.get("suburb"),
                address.get("city") or address.get("town") or address.get("village"),
                address.get("state"),
                address.get("country"),
            ]
            formatted_address = ", ".join(p for p in address_parts if p) or None

            kinds = data.get("kinds", "")
            types_list = [k.strip() for k in kinds.split(",") if k.strip()]

            wiki = data.get("wikipedia_extracts", {})
            description = wiki.get("text") or data.get("info", {}).get("descr") if isinstance(data.get("info"), dict) else None

            preview = data.get("preview", {})
            photos = []
            if preview and preview.get("source"):
                photos_raw = [{"photo_reference": preview["source"], "proxy_url": preview["source"]}]
                from backend.app.travel.schemas.internal import TravelPhoto
                photos = [TravelPhoto(**p) for p in photos_raw]

            return TravelPlace(
                name=data.get("name") or "Place",
                place_id=data.get("xid"),
                formatted_address=formatted_address,
                latitude=float(lat) if lat is not None else None,
                longitude=float(lon) if lon is not None else None,
                types=types_list,
                rating=data.get("rate"),
                website_url=data.get("url"),
                photos=photos,
                provider="opentripmap",
                provider_id=data.get("xid"),
                metadata={"kinds": kinds, "description": description},
            )
        except Exception:
            return None

    @staticmethod
    def normalize_autocomplete(data: Any) -> List[TravelPlaceAutocompleteItem]:
        """Normalize autosuggest results into autocomplete suggestion list."""
        suggestions: List[TravelPlaceAutocompleteItem] = []

        if isinstance(data, dict):
            items = data.get("features", data.get("response", []))
        elif isinstance(data, list):
            items = data
        else:
            return suggestions

        for item in items:
            try:
                if isinstance(item, dict) and item.get("type") == "Feature":
                    props = item.get("properties", {})
                else:
                    props = item

                xid = props.get("xid") or props.get("id") or ""
                name = props.get("name") or ""
                country = props.get("country") or props.get("address", {}).get("country", "") if isinstance(props.get("address"), dict) else ""
                secondary = country or props.get("kinds", "").split(",")[0].replace("_", " ").title()

                suggestions.append(
                    TravelPlaceAutocompleteItem(
                        place_id=xid,
                        primary_text=name,
                        secondary_text=secondary or None,
                        full_text=f"{name}, {secondary}".strip(", ") if secondary else name,
                        types=[k.strip() for k in props.get("kinds", "").split(",") if k.strip()],
                        provider="opentripmap",
                    )
                )
            except Exception:
                continue

        return suggestions
