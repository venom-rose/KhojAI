import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class UserIntent(str, Enum):
    DESTINATION_DISCOVERY = "DESTINATION_DISCOVERY"
    HOTEL_SEARCH = "HOTEL_SEARCH"
    FLIGHT_SEARCH = "FLIGHT_SEARCH"
    ITINERARY_PLANNING = "ITINERARY_PLANNING"
    PLACE_INQUIRY = "PLACE_INQUIRY"
    WEATHER_INQUIRY = "WEATHER_INQUIRY"
    ROUTE_CALCULATION = "ROUTE_CALCULATION"
    RESTAURANT_SEARCH = "RESTAURANT_SEARCH"
    TRIP_MANAGEMENT = "TRIP_MANAGEMENT"
    GENERAL_TRAVEL_CHAT = "GENERAL_TRAVEL_CHAT"


@dataclass
class IntentAnalysis:
    """Outcome of intent detection and entity parsing."""
    intent: UserIntent
    required_tools: List[str]
    entities: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


class IntentDetector:
    """Classifies user travel query intent, extracts entities, and selects required tools."""

    # Common Indian destination keywords for entity extraction
    COMMON_DESTINATIONS = [
        "rajasthan", "jaipur", "udaipur", "jodhpur", "jaisalmer", "pushkar", "bikaner",
        "kerala", "munnar", "wayanad", "alleppey", "kochi", "varkala",
        "himachal", "manali", "shimla", "spiti", "dharamshala", "kasol", "jibhi",
        "uttarakhand", "rishikesh", "dehradun", "mussoorie", "nainital",
        "goa", "delhi", "mumbai", "kolkata", "bengaluru", "chennai", "hyderabad",
        "varanasi", "agra", "amritsar", "ladakh", "leh", "srinagar", "kashmir",
        "meghalaya", "shillong", "cherrapunji", "arunachal", "ziro", "sikkim", "gangtok",
        "india",
    ]

    def detect(self, user_query: str) -> IntentAnalysis:
        """Analyze user query using semantic heuristics and entity parsing."""
        q = user_query.strip().lower()
        entities: Dict[str, Any] = {}

        # 1. Extract days / duration
        day_match = re.search(r"(\d+)\s*[- ]*(day|days|night|nights)", q)
        if day_match:
            entities["days"] = int(day_match.group(1))

        # 2. Extract potential destination from query
        for dest in self.COMMON_DESTINATIONS:
            if re.search(r"\b" + re.escape(dest) + r"\b", q):
                if "destination" not in entities:
                    entities["destination"] = dest.title()
                elif "secondary_destination" not in entities:
                    entities["secondary_destination"] = dest.title()

        # 3. Detect flight origin & destination (e.g., "from Kolkata to Delhi")
        flight_route = re.search(r"from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)", q)
        if flight_route:
            entities["origin"] = flight_route.group(1).strip().title()
            entities["destination"] = flight_route.group(2).strip().title()

        # 4. Check specific intents

        # A. Flight search (e.g. "Find me flights from Kolkata to Delhi")
        if any(w in q for w in ["flight", "flights", "fly to", "air ticket", "airline"]):
            return IntentAnalysis(
                intent=UserIntent.FLIGHT_SEARCH,
                required_tools=["search_flights"],
                entities=entities,
            )

        # B. Itinerary Planning (e.g. "Plan a 5-day Rajasthan trip", "itinerary for 3 days")
        if any(w in q for w in ["plan a", "plan me", "itinerary", "day trip", "days trip", "tour plan"]) or (
            "days" in entities and any(w in q for w in ["trip", "visit", "travel", "tour"])
        ):
            tools = [
                "search_destinations",
                "search_attractions",
                "search_activities",
                "search_hotels",
                "calculate_distance",
                "create_itinerary",
            ]
            return IntentAnalysis(
                intent=UserIntent.ITINERARY_PLANNING,
                required_tools=tools,
                entities=entities,
            )

        # C. Hotel search (e.g. "Find hotels in Jaipur", "places to stay in Goa")
        if any(w in q for w in ["hotel", "hotels", "homestay", "resort", "stay in", "accommodations"]):
            return IntentAnalysis(
                intent=UserIntent.HOTEL_SEARCH,
                required_tools=["search_hotels", "search_places"],
                entities=entities,
            )

        # D. Weather inquiry (e.g. "weather in Manali", "best time to visit Kerala")
        if any(w in q for w in ["weather", "climate", "temperature", "rain", "monsoon", "season", "best time to visit"]):
            return IntentAnalysis(
                intent=UserIntent.WEATHER_INQUIRY,
                required_tools=["get_weather"],
                entities=entities,
            )

        # E. Distance / route calculation
        if any(w in q for w in ["distance between", "how far is", "driving time", "drive from", "route from"]):
            if "and" in q or "to" in q:
                return IntentAnalysis(
                    intent=UserIntent.ROUTE_CALCULATION,
                    required_tools=["calculate_distance"],
                    entities=entities,
                )

        # F. Restaurant search
        if any(w in q for w in ["restaurant", "restaurants", "food", "cafe", "eat in", "dining", "dhaba"]):
            return IntentAnalysis(
                intent=UserIntent.RESTAURANT_SEARCH,
                required_tools=["search_restaurants"],
                entities=entities,
            )

        # G. Place details / POI inquiry
        if any(w in q for w in ["about hawa mahal", "details of", "history of", "opening hours of", "ticket price of"]):
            return IntentAnalysis(
                intent=UserIntent.PLACE_INQUIRY,
                required_tools=["get_place_details", "search_places"],
                entities=entities,
            )

        # H. Trip saving / retrieval
        if any(w in q for w in ["save my trip", "save itinerary", "save this plan"]):
            return IntentAnalysis(
                intent=UserIntent.TRIP_MANAGEMENT,
                required_tools=["save_trip"],
                entities=entities,
            )
        if any(w in q for w in ["load trip", "my saved trips", "retrieve trip", "show my trip"]):
            return IntentAnalysis(
                intent=UserIntent.TRIP_MANAGEMENT,
                required_tools=["retrieve_trip"],
                entities=entities,
            )

        # I. Destination discovery (e.g. "Best places to visit in India?", "Hidden gems in Himachal")
        if any(w in q for w in ["best places", "places to visit", "where to go", "recommend destinations", "offbeat spots", "explore"]):
            return IntentAnalysis(
                intent=UserIntent.DESTINATION_DISCOVERY,
                required_tools=["search_destinations"],
                entities=entities,
            )

        # Default: General travel inquiry (uses search_destinations if a destination was recognized)
        if "destination" in entities:
            return IntentAnalysis(
                intent=UserIntent.DESTINATION_DISCOVERY,
                required_tools=["search_destinations"],
                entities=entities,
            )

        return IntentAnalysis(
            intent=UserIntent.GENERAL_TRAVEL_CHAT,
            required_tools=["search_local_database"],
            entities=entities,
        )
