import logging
from typing import Any, Dict, List, Optional
from backend.app.ai.orchestration.intent_detector import IntentAnalysis, UserIntent
from backend.app.ai.tools.registry import ToolRegistry, default_tool_registry

logger = logging.getLogger(__name__)


class ToolSelector:
    """Selects and binds execution arguments for required travel tools."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or default_tool_registry

    def resolve_tool_calls(
        self,
        analysis: IntentAnalysis,
        user_query: str,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Determine the parameter dictionary for each required tool."""
        tool_calls: List[Dict[str, Any]] = []
        dest = analysis.entities.get("destination", "India")
        origin = analysis.entities.get("origin", "Delhi")
        days = analysis.entities.get("days", 5)

        for tool_name in analysis.required_tools:
            tool = self.registry.get(tool_name)
            if not tool:
                logger.warning(f"Required tool '{tool_name}' not found in registry; skipping.")
                continue

            args: Dict[str, Any] = {}

            if tool_name == "search_destinations":
                args = {"query": dest if dest != "India" else user_query, "limit": 4}
            elif tool_name == "search_hotels":
                args = {"city": dest, "limit": 4}
            elif tool_name == "search_places":
                args = {"query": f"{dest} attractions and landmarks", "limit": 4}
            elif tool_name == "search_attractions":
                args = {"destination": dest, "limit": 4}
            elif tool_name == "search_activities":
                args = {"destination": dest, "limit": 4}
            elif tool_name == "search_restaurants":
                args = {"city": dest, "limit": 4}
            elif tool_name == "search_flights":
                args = {"origin": origin, "destination": dest, "adults": 1}
            elif tool_name == "search_airports":
                args = {"keyword": dest}
            elif tool_name == "get_weather":
                args = {"destination": dest}
            elif tool_name == "calculate_distance":
                secondary = analysis.entities.get("secondary_destination", "Jaipur")
                args = {"origin": dest, "destination": secondary}
            elif tool_name == "calculate_route":
                args = {"stops": [dest, "Jaipur", "Jodhpur"]}
            elif tool_name == "create_itinerary":
                args = {"destination": dest, "days": days, "travel_style": "slow travel"}
            elif tool_name == "search_local_database":
                args = {"query": user_query, "limit_per_category": 3}
            elif tool_name == "get_user_preferences":
                args = {"user_id": user_id}
            elif tool_name == "save_trip":
                args = {
                    "title": f"Journey to {dest}",
                    "summary": f"Curated travel plan for {dest}",
                    "user_id": user_id,
                }
            elif tool_name == "retrieve_trip":
                args = {"trip_identifier": dest}
            elif tool_name == "get_place_details":
                args = {"place_id": dest}

            tool_calls.append({
                "tool_name": tool_name,
                "tool_instance": tool,
                "kwargs": args,
            })

        return tool_calls
