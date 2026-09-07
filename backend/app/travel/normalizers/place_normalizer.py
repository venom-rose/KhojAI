"""Place and Point-of-Interest normalizer for Google Places, OpenTripMap, Geoapify, and Local DB."""

from typing import Any, Dict, List, Optional
from backend.app.travel.schemas.internal import (
    TravelPhoto,
    TravelPlace,
    TravelPlaceAutocompleteItem,
    TravelReview,
)


class PlaceNormalizer:
    """Normalizes places, attractions, and autocomplete items into TravelPlace schemas."""

    @staticmethod
    def normalize_google(place_data: Dict[str, Any]) -> TravelPlace:
        """Normalize Google Places API (New) response."""
        loc = place_data.get("location", {})
        display_name = place_data.get("displayName", {}).get("text") or place_data.get("name") or "Unnamed Place"

        photos = []
        for p in place_data.get("photos", []):
            photo_name = p.get("name", "")
            attributions = [a.get("displayName") for a in p.get("authorAttributions", []) if a.get("displayName")]
            photos.append(
                TravelPhoto(
                    photo_reference=photo_name,
                    height=p.get("heightPx"),
                    width=p.get("widthPx"),
                    author_attributions=attributions,
                    proxy_url=f"/api/v1/travel/places/photos/{photo_name}" if photo_name else None,
                )
            )

        reviews = []
        for r in place_data.get("reviews", []):
            author = r.get("authorAttribution", {}).get("displayName") or "Traveler"
            text_val = r.get("text", {}).get("text") if isinstance(r.get("text"), dict) else r.get("text")
            reviews.append(
                TravelReview(
                    author_name=author,
                    rating=r.get("rating"),
                    text=text_val,
                    relative_publish_time=r.get("relativePublishTimeDescription"),
                )
            )

        return TravelPlace(
            name=display_name,
            place_id=place_data.get("id"),
            formatted_address=place_data.get("formattedAddress"),
            latitude=loc.get("latitude"),
            longitude=loc.get("longitude"),
            types=place_data.get("types", []),
            rating=place_data.get("rating"),
            user_rating_count=place_data.get("userRatingCount"),
            price_level=place_data.get("priceLevel"),
            photos=photos,
            reviews=reviews,
            phone_number=place_data.get("nationalPhoneNumber"),
            website_url=place_data.get("websiteUri"),
            opening_hours=place_data.get("regularOpeningHours", {}).get("weekdayDescriptions", []),
            is_open_now=place_data.get("regularOpeningHours", {}).get("openNow"),
            provider="google_places",
            provider_id=place_data.get("id"),
        )

    @staticmethod
    def normalize_google_autocomplete(suggestion: Dict[str, Any]) -> TravelPlaceAutocompleteItem:
        """Normalize Google Places Autocomplete suggestion."""
        prediction = suggestion.get("placePrediction", suggestion)
        text_info = prediction.get("text", {})
        structured_format = prediction.get("structuredFormat", {})

        return TravelPlaceAutocompleteItem(
            place_id=prediction.get("placeId", ""),
            primary_text=structured_format.get("mainText", {}).get("text", text_info.get("text", "")),
            secondary_text=structured_format.get("secondaryText", {}).get("text"),
            full_text=text_info.get("text", ""),
            types=prediction.get("types", []),
            provider="google_places",
        )

    @staticmethod
    def normalize_opentripmap(feature_or_detail: Dict[str, Any]) -> TravelPlace:
        """Normalize OpenTripMap feature or xid detail."""
        # If it's a detail dictionary
        if "xid" in feature_or_detail and "point" in feature_or_detail:
            point = feature_or_detail.get("point", {})
            name = feature_or_detail.get("name") or "Historical Landmark"
            address_obj = feature_or_detail.get("address", {})
            formatted_addr = ", ".join(filter(None, [
                address_obj.get("road"),
                address_obj.get("suburb"),
                address_obj.get("city"),
                address_obj.get("state"),
                address_obj.get("country"),
            ]))
            preview = feature_or_detail.get("preview", {})
            photos = []
            if preview.get("source"):
                photos.append(TravelPhoto(photo_reference=preview["source"], proxy_url=preview["source"]))

            kinds = feature_or_detail.get("kinds", "").split(",") if feature_or_detail.get("kinds") else []

            return TravelPlace(
                name=name,
                place_id=feature_or_detail.get("xid"),
                formatted_address=formatted_addr or None,
                latitude=point.get("lat"),
                longitude=point.get("lon"),
                types=kinds,
                rating=float(feature_or_detail.get("rate", 3)),
                photos=photos,
                website_url=feature_or_detail.get("url"),
                provider="opentripmap",
                provider_id=feature_or_detail.get("xid"),
                metadata={"wikipedia": feature_or_detail.get("wikipedia")},
            )

        # If it's a GeoJSON feature from radius search
        props = feature_or_detail.get("properties", {})
        geom = feature_or_detail.get("geometry", {})
        coords = geom.get("coordinates", [None, None])

        return TravelPlace(
            name=props.get("name") or "Landmark",
            place_id=props.get("xid"),
            latitude=coords[1] if len(coords) > 1 else None,
            longitude=coords[0] if len(coords) > 0 else None,
            types=props.get("kinds", "").split(",") if props.get("kinds") else [],
            rating=float(props.get("rate", 3)),
            provider="opentripmap",
            provider_id=props.get("xid"),
        )

    @staticmethod
    def normalize_geoapify(feature: Dict[str, Any]) -> TravelPlace:
        """Normalize Geoapify Place feature."""
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [None, None])
        lon = coords[0] if len(coords) > 0 else props.get("lon")
        lat = coords[1] if len(coords) > 1 else props.get("lat")

        name = props.get("name") or props.get("address_line1") or "Point of Interest"
        formatted_address = props.get("formatted") or props.get("address_line2") or ""

        return TravelPlace(
            name=name,
            place_id=props.get("place_id") or str(props.get("osm_id", "")),
            formatted_address=formatted_address,
            latitude=lat,
            longitude=lon,
            types=props.get("categories", []),
            phone_number=props.get("contact", {}).get("phone"),
            website_url=props.get("website"),
            provider="geoapify",
            provider_id=props.get("place_id"),
            metadata={"datasource": props.get("datasource", {})},
        )

    @staticmethod
    def normalize_local(item: Any) -> TravelPlace:
        """Normalize a local database Attraction or Point of Interest."""
        if isinstance(item, dict):
            return TravelPlace(
                name=item["name"],
                place_id=str(item.get("id", "")),
                formatted_address=item.get("address") or item.get("city_name"),
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                types=[item.get("category", "attraction")] + item.get("tags", []),
                rating=4.5,
                provider="local_db",
                provider_id=str(item.get("id", "")),
            )
        return TravelPlace(
            name=item.name,
            place_id=str(item.id),
            formatted_address=getattr(item, "timings", None),
            latitude=item.latitude,
            longitude=item.longitude,
            types=[item.category] + getattr(item, "tags", []),
            rating=4.8,
            provider="local_db",
            provider_id=str(item.id),
        )
