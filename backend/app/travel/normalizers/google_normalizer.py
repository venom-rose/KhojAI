"""Normalizers converting raw Google Places API (New) responses into internal travel schemas."""

from typing import Any, Dict, List, Optional
from backend.app.travel.schemas.internal import (
    TravelPhoto,
    TravelPlace,
    TravelPlaceAutocompleteItem,
    TravelReview,
)


class GooglePlacesNormalizer:
    """Transforms Google Places API (New) JSON payloads into TravelPlace instances."""

    @classmethod
    def normalize_single_place(cls, place: Dict[str, Any]) -> TravelPlace:
        display_name = place.get("displayName", {})
        name = display_name.get("text") if isinstance(display_name, dict) else place.get("name", "Unnamed Place")
        location = place.get("location", {})

        # Photos
        photos: List[TravelPhoto] = []
        for p in place.get("photos", []):
            photo_name = p.get("name", "")
            photos.append(
                TravelPhoto(
                    photo_reference=photo_name,
                    height=p.get("heightPx"),
                    width=p.get("widthPx"),
                    author_attributions=[
                        a.get("displayName", "") for a in p.get("authorAttributions", []) if a.get("displayName")
                    ],
                    proxy_url=f"/api/v1/travel/places/photos/{photo_name}" if photo_name else None,
                )
            )

        # Reviews
        reviews: List[TravelReview] = []
        for r in place.get("reviews", []):
            author_data = r.get("authorAttribution", {})
            text_data = r.get("text", {})
            review_text = text_data.get("text") if isinstance(text_data, dict) else str(text_data) if text_data else None
            reviews.append(
                TravelReview(
                    author_name=author_data.get("displayName", "Verified Traveler"),
                    rating=float(r.get("rating")) if r.get("rating") is not None else None,
                    text=review_text,
                    relative_publish_time=r.get("relativePublishTimeDescription"),
                    language=r.get("originalText", {}).get("languageCode") if isinstance(r.get("originalText"), dict) else None,
                )
            )

        # Opening hours
        opening_hours: List[str] = []
        reg_hours = place.get("regularOpeningHours", {})
        if reg_hours:
            opening_hours = reg_hours.get("weekdayDescriptions", [])

        # Price level
        price_level_raw = place.get("priceLevel")
        price_map = {
            "PRICE_LEVEL_INEXPENSIVE": "₹",
            "PRICE_LEVEL_MODERATE": "₹₹",
            "PRICE_LEVEL_EXPENSIVE": "₹₹₹",
            "PRICE_LEVEL_VERY_EXPENSIVE": "₹₹₹₹",
        }
        price_level = price_map.get(price_level_raw, "₹₹")

        return TravelPlace(
            name=name,
            place_id=place.get("id"),
            formatted_address=place.get("formattedAddress"),
            latitude=location.get("latitude"),
            longitude=location.get("longitude"),
            types=place.get("types", []),
            rating=float(place.get("rating")) if place.get("rating") is not None else None,
            user_rating_count=place.get("userRatingCount"),
            price_level=price_level,
            photos=photos,
            reviews=reviews,
            phone_number=place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber"),
            website_url=place.get("websiteUri"),
            opening_hours=opening_hours,
            is_open_now=reg_hours.get("openNow"),
            provider="google_places",
            provider_id=place.get("id"),
            metadata={"business_status": place.get("businessStatus")},
        )

    @classmethod
    def normalize_places(cls, payload: Dict[str, Any]) -> List[TravelPlace]:
        places_raw = payload.get("places", [])
        return [cls.normalize_single_place(p) for p in places_raw]

    @classmethod
    def normalize_autocomplete(cls, payload: Dict[str, Any]) -> List[TravelPlaceAutocompleteItem]:
        suggestions_raw = payload.get("suggestions", [])
        items: List[TravelPlaceAutocompleteItem] = []

        for item in suggestions_raw:
            pred = item.get("placePrediction", {})
            place_id = pred.get("placeId") or pred.get("place")
            if not place_id:
                continue

            text_obj = pred.get("text", {})
            full_text = text_obj.get("text", "")

            struct = pred.get("structuredFormat", {})
            main_text = struct.get("mainText", {}).get("text", full_text)
            sec_text = struct.get("secondaryText", {}).get("text")

            items.append(
                TravelPlaceAutocompleteItem(
                    place_id=place_id,
                    primary_text=main_text,
                    secondary_text=sec_text,
                    full_text=full_text,
                    types=pred.get("types", []),
                    provider="google_places",
                )
            )
        return items
