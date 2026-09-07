"""Response Normalizer for KHOJAI AI Travel Agent.

Extracts and normalizes raw tool execution outputs into a unified schema of
structured travel cards that the frontend can deterministically render:
- destination
- hotel
- activity
- flight
- itinerary
- map
- error
"""

import logging
from typing import Any, Dict, List, Optional
from backend.app.ai.tools.base import ToolResult

logger = logging.getLogger("khojai.ai.response_normalizer")


class ResponseNormalizer:
    """Normalizes tool execution results into a unified structured cards schema."""

    @staticmethod
    def normalize_tool_results(tool_results: List[ToolResult]) -> List[Dict[str, Any]]:
        """Parse tool results into an ordered list of structured cards."""
        cards: List[Dict[str, Any]] = []

        for result in tool_results:
            if not result.success:
                cards.append({
                    "type": "error",
                    "data": {
                        "tool": result.tool_name,
                        "message": result.message or "Service temporarily unavailable",
                        "warning": result.warning,
                    },
                })
                continue

            tool_name = result.tool_name
            data = result.data

            if tool_name == "search_destinations":
                cards.extend(ResponseNormalizer._extract_destinations(data))
            elif tool_name == "search_hotels":
                cards.extend(ResponseNormalizer._extract_hotels(data))
            elif tool_name in ("search_activities", "search_attractions"):
                cards.extend(ResponseNormalizer._extract_activities(data, tool_name))
            elif tool_name == "search_flights":
                cards.extend(ResponseNormalizer._extract_flights(data))
            elif tool_name == "create_itinerary":
                card = ResponseNormalizer._extract_itinerary(data)
                if card:
                    cards.append(card)
            elif tool_name in ("search_places", "get_place_details"):
                cards.extend(ResponseNormalizer._extract_places_and_maps(data))
            elif tool_name == "get_personalized_recommendations":
                cards.extend(ResponseNormalizer._extract_personalized_recommendations(data))

        return cards

    @staticmethod
    def _extract_destinations(data: Any) -> List[Dict[str, Any]]:
        cards = []
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items[:4]:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            cards.append({
                "type": "destination",
                "data": {
                    "id": item.get("id") or item.get("slug") or name.lower().replace(" ", "-"),
                    "name": name,
                    "state": item.get("state", "India"),
                    "region": item.get("region", "India"),
                    "category": item.get("category", "Heritage & Nature"),
                    "best_season": item.get("best_season", "Oct – Mar"),
                    "budget": item.get("budget", "₹₹"),
                    "trust_score": item.get("trust_score", 92),
                    "description": item.get("description"),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "image": item.get("image", "/images/hero-himalayas.jpg"),
                },
            })
            if item.get("latitude") and item.get("longitude"):
                cards.append({
                    "type": "map",
                    "data": {
                        "title": f"Location: {name}",
                        "latitude": item.get("latitude"),
                        "longitude": item.get("longitude"),
                        "description": f"{name}, {item.get('state', '')}",
                        "zoom": 11,
                    },
                })
        return cards

    @staticmethod
    def _extract_hotels(data: Any) -> List[Dict[str, Any]]:
        cards = []
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items[:4]:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            cards.append({
                "type": "hotel",
                "data": {
                    "id": item.get("id") or name.lower().replace(" ", "-"),
                    "name": name,
                    "city": item.get("city", ""),
                    "price_tier": item.get("price_tier", "₹₹"),
                    "price_per_night_inr": item.get("price_per_night_inr") or item.get("price_inr") or 3500,
                    "rating": item.get("rating", 4.5),
                    "stay_type": item.get("stay_type", "Boutique Homestay"),
                    "address": item.get("address", ""),
                    "amenities": item.get("amenities") or ["Wifi", "Breakfast", "Local Host"],
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                },
            })
        return cards

    @staticmethod
    def _extract_activities(data: Any, tool_name: str) -> List[Dict[str, Any]]:
        cards = []
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items[:4]:
            if not isinstance(item, dict):
                continue
            title = item.get("name") or item.get("title")
            if not title:
                continue
            cards.append({
                "type": "activity",
                "data": {
                    "id": item.get("id") or title.lower().replace(" ", "-"),
                    "title": title,
                    "destination": item.get("destination") or item.get("city", ""),
                    "category": item.get("category", "Culture & Heritage"),
                    "duration_hours": item.get("duration_hours", 2.0),
                    "price_inr": item.get("price_inr") or item.get("admission_fee_inr") or 0,
                    "recommended_timing": item.get("recommended_timing", "Morning / Afternoon"),
                    "description": item.get("description", ""),
                    "requires_guide": item.get("requires_guide", False),
                    "is_attraction": tool_name == "search_attractions",
                },
            })
        return cards

    @staticmethod
    def _extract_flights(data: Any) -> List[Dict[str, Any]]:
        cards = []
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items[:3]:
            if not isinstance(item, dict):
                continue
            cards.append({
                "type": "flight",
                "data": {
                    "airline": item.get("airline", "IndiGo / Air India"),
                    "flight_number": item.get("flight_number", "6E-204"),
                    "origin": item.get("origin", "DEL"),
                    "destination": item.get("destination", "BOM"),
                    "departure_time": item.get("departure_time", "08:30"),
                    "arrival_time": item.get("arrival_time", "10:45"),
                    "duration": item.get("duration", "2h 15m"),
                    "stops": item.get("stops", 0),
                    "price_inr": item.get("price_inr", 4850),
                    "is_estimate": not item.get("is_live", False),
                },
            })
        return cards

    @staticmethod
    def _extract_itinerary(data: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(data, dict):
            return None
        return {
            "type": "itinerary",
            "data": {
                "summary": data.get("summary", ""),
                "destination": data.get("destination", ""),
                "duration_days": data.get("duration_days", len(data.get("days", []))),
                "pacing_rating": data.get("pacing_rating", "Unhurried & Immersive"),
                "estimated_cost": data.get("estimated_cost", {}),
                "days": data.get("days", []),
                "curator_notes": data.get("curator_notes", []),
            },
        }

    @staticmethod
    def _extract_places_and_maps(data: Any) -> List[Dict[str, Any]]:
        cards = []
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items[:3]:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("title")
            if not name:
                continue
            cards.append({
                "type": "activity",
                "data": {
                    "id": item.get("id", name.lower().replace(" ", "-")),
                    "title": name,
                    "category": item.get("category", "Point of Interest"),
                    "description": item.get("description") or item.get("address", ""),
                    "duration_hours": 1.5,
                    "price_inr": 0,
                    "is_attraction": True,
                },
            })
            if item.get("latitude") and item.get("longitude"):
                cards.append({
                    "type": "map",
                    "data": {
                        "title": name,
                        "latitude": float(item.get("latitude")),
                        "longitude": float(item.get("longitude")),
                        "description": item.get("address", ""),
                        "zoom": 13,
                    },
                })
        return cards

    @staticmethod
    def _extract_personalized_recommendations(data: Any) -> List[Dict[str, Any]]:
        cards = []
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items[:4]:
            if not isinstance(item, dict):
                continue
            entity_type = item.get("entity_type", "destination")
            details = item.get("details", {})
            title = item.get("title", "")
            explanation = item.get("explanation", "")
            score = item.get("score", 90)

            if entity_type == "destination":
                cards.append({
                    "type": "destination",
                    "data": {
                        "id": item.get("entity_id", title.lower().replace(" ", "-")),
                        "name": title,
                        "state": details.get("state", "India"),
                        "region": details.get("region", "India"),
                        "category": details.get("category", "Heritage"),
                        "trust_score": int(score),
                        "description": details.get("description", ""),
                        "explanation": explanation,
                        "match_breakdown": item.get("match_breakdown"),
                    },
                })
            elif entity_type == "hotel":
                cards.append({
                    "type": "hotel",
                    "data": {
                        "id": item.get("entity_id", title.lower().replace(" ", "-")),
                        "name": title,
                        "city": details.get("city", ""),
                        "price_tier": details.get("price_tier", "₹₹"),
                        "price_per_night_inr": details.get("price_per_night_inr", 3500),
                        "rating": details.get("rating", 4.6),
                        "stay_type": details.get("stay_type", "Homestay"),
                        "explanation": explanation,
                        "match_breakdown": item.get("match_breakdown"),
                    },
                })
            elif entity_type == "activity":
                cards.append({
                    "type": "activity",
                    "data": {
                        "id": item.get("entity_id", title.lower().replace(" ", "-")),
                        "title": title,
                        "category": details.get("category", "Experience"),
                        "duration_hours": details.get("duration_hours", 2.0),
                        "price_inr": details.get("price_inr", 0),
                        "explanation": explanation,
                        "match_breakdown": item.get("match_breakdown"),
                    },
                })
        return cards
