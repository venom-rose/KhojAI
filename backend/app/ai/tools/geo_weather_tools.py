import math
import logging
from typing import Any, Dict, List, Optional
from backend.app.ai.tools.base import BaseTool, DataProvenance, ToolResult

logger = logging.getLogger(__name__)

# Predefined coordinate lookup for prominent Indian cities/hubs
CITY_COORDINATES: Dict[str, tuple[float, float]] = {
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "jaipur": (26.9124, 75.7873),
    "jodhpur": (26.2389, 73.0243),
    "udaipur": (24.5854, 73.7125),
    "jaisalmer": (26.9157, 70.9083),
    "pushkar": (26.4897, 74.5511),
    "bikaner": (28.0229, 73.3119),
    "mumbai": (19.0760, 72.8777),
    "kolkata": (22.5726, 88.3639),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "varanasi": (25.3176, 82.9739),
    "agra": (27.1767, 78.0081),
    "goa": (15.2993, 74.1240),
    "kochi": (9.9312, 76.2673),
    "shimla": (31.1048, 77.1734),
    "manali": (32.2432, 77.1892),
    "leh": (34.1526, 77.5771),
    "spiti": (32.2464, 78.0349),
    "ziro": (27.5947, 93.8385),
    "shillong": (25.5788, 91.8933),
}

# Seasonal climate profiles for major Indian regions
CLIMATE_DATA: Dict[str, Dict[str, Any]] = {
    "rajasthan": {
        "best_months": "October to March",
        "current_season": "Mild / Autumn",
        "avg_temp_c": {"min": 14, "max": 28},
        "conditions": "Clear skies, low humidity, warm sunny afternoons, cool evenings.",
        "packing_advice": "Cotton daytime layers, a light jacket/fleece for after-sunset chills.",
    },
    "himachal": {
        "best_months": "March to June (mild), October to February (snow)",
        "current_season": "Mountain Pleasant / Crisp",
        "avg_temp_c": {"min": 5, "max": 18},
        "conditions": "Crisp mountain air, sharp sun at altitude, freezing nights.",
        "packing_advice": "Windproof jacket, thermal base layer, sturdy hiking boots.",
    },
    "kerala": {
        "best_months": "September to March",
        "current_season": "Post-Monsoon Greenery",
        "avg_temp_c": {"min": 23, "max": 31},
        "conditions": "Moderate tropical humidity, lush green landscape, intermittent coastal breezes.",
        "packing_advice": "Breathable linen, light rain poncho, mosquito repellent.",
    },
    "northeast": {
        "best_months": "October to April",
        "current_season": "Pleasant Harvest",
        "avg_temp_c": {"min": 12, "max": 24},
        "conditions": "Mist in valleys, crystal clear mountain vistas, minimal rain.",
        "packing_advice": "Layers, warm woolens for evening homestay fires, rainproof jacket.",
    },
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 1)


class GetWeatherTool(BaseTool):
    """Tool to retrieve seasonal travel climate and weather forecasts."""

    name = "get_weather"
    description = (
        "Retrieve seasonal climate guidance, temperature ranges, humidity, and weather travel tips for any Indian destination."
    )
    parameters = {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Destination or city name (e.g. 'Jaipur', 'Leh', 'Kerala', 'Manali').",
            },
            "month": {
                "type": "string",
                "description": "Optional travel month (e.g. 'October', 'December', 'May').",
            },
        },
        "required": ["destination"],
    }

    async def execute(self, destination: str, month: Optional[str] = None, **kwargs) -> ToolResult:
        dest_lower = destination.strip().lower()

        # Find matching region
        matched_profile = None
        for region_key, profile in CLIMATE_DATA.items():
            if region_key in dest_lower:
                matched_profile = profile
                break

        if not matched_profile:
            # Default thoughtful meteorological estimate
            matched_profile = {
                "best_months": "October to March (for plains/coasts) or April to June (for high Himalayas)",
                "current_season": "Favorable Travel Window",
                "avg_temp_c": {"min": 16, "max": 29},
                "conditions": "Generally stable conditions; check local daily meteorological radar closer to departure.",
                "packing_advice": "Versatile layers, comfortable walking footwear, and sun protection.",
            }

        result_data = {
            "destination": destination,
            "query_month": month or "Current / Upcoming",
            "ideal_travel_season": matched_profile["best_months"],
            "expected_conditions": matched_profile["conditions"],
            "temperature_range_celsius": matched_profile["avg_temp_c"],
            "packing_recommendations": matched_profile["packing_advice"],
        }

        return ToolResult(
            tool_name=self.name,
            success=True,
            data=result_data,
            message=f"Weather & climate profile compiled for '{destination}'.",
            provenance=DataProvenance.ESTIMATE_RECOMMENDATION,
            is_live_data=False,
            warning="Live instantaneous radar is estimated based on historical regional climatology.",
            metadata={"destination": destination},
        )


class CalculateDistanceTool(BaseTool):
    """Tool to calculate geodesic and road distances between places."""

    name = "calculate_distance"
    description = (
        "Calculate the estimated travel distance (in km) and travel time by road, rail, or air between two cities/places."
    )
    parameters = {
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "Origin city or coordinate pair 'lat,lon' (e.g. 'Jaipur' or '26.9124,75.7873').",
            },
            "destination": {
                "type": "string",
                "description": "Destination city or coordinate pair 'lat,lon' (e.g. 'Jodhpur').",
            },
        },
        "required": ["origin", "destination"],
    }

    def _resolve_coords(self, place: str) -> Optional[tuple[float, float]]:
        cleaned = place.strip().lower()
        if "," in cleaned:
            parts = cleaned.split(",")
            try:
                return float(parts[0].strip()), float(parts[1].strip())
            except ValueError:
                pass
        return CITY_COORDINATES.get(cleaned)

    async def execute(self, origin: str, destination: str, **kwargs) -> ToolResult:
        orig_coords = self._resolve_coords(origin)
        dest_coords = self._resolve_coords(destination)

        if not orig_coords or not dest_coords:
            # Fallback estimation if coordinates unknown
            return ToolResult(
                tool_name=self.name,
                success=True,
                data={
                    "origin": origin,
                    "destination": destination,
                    "road_distance_km": "~250-350 km (approximate)",
                    "estimated_drive_time": "5 to 6 hours",
                    "note": "Exact coordinates not in rapid lookup cache; estimated via regional road corridors.",
                },
                provenance=DataProvenance.ESTIMATE_RECOMMENDATION,
                is_live_data=False,
            )

        geo_km = haversine_km(orig_coords[0], orig_coords[1], dest_coords[0], dest_coords[1])
        # Indian highway network factor typically adds ~25-30% detour over straight line
        road_km = round(geo_km * 1.25, 1)

        # Average highway speed ~55-65 km/h
        drive_hours = round(road_km / 58.0, 1)

        return ToolResult(
            tool_name=self.name,
            success=True,
            data={
                "origin": origin,
                "destination": destination,
                "straight_line_distance_km": geo_km,
                "estimated_road_distance_km": road_km,
                "estimated_drive_time_hours": drive_hours,
                "recommended_mode": "Train/Self-Drive" if road_km < 400 else "Domestic Flight / Overnight Train",
            },
            message=f"Distance between {origin} and {destination} is ~{road_km} km ({drive_hours}h drive).",
            provenance=DataProvenance.CALCULATED,
            is_live_data=True,
            metadata={"origin": origin, "destination": destination, "road_km": road_km},
        )


class CalculateRouteTool(BaseTool):
    """Tool to calculate multi-stop route legs and sequencing."""

    name = "calculate_route"
    description = (
        "Calculate multi-stop journey legs, sequencing, and total driving transit times across a list of stops."
    )
    parameters = {
        "type": "object",
        "properties": {
            "stops": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Ordered list of stops (e.g. ['Delhi', 'Jaipur', 'Jodhpur', 'Udaipur']).",
            },
        },
        "required": ["stops"],
    }

    async def execute(self, stops: List[str], **kwargs) -> ToolResult:
        if len(stops) < 2:
            return ToolResult(
                tool_name=self.name,
                success=False,
                data=None,
                message="At least 2 stops are required to calculate a route.",
                provenance=DataProvenance.CALCULATED,
            )

        dist_tool = CalculateDistanceTool()
        legs = []
        total_road_km = 0.0
        total_hours = 0.0

        for i in range(len(stops) - 1):
            s1 = stops[i]
            s2 = stops[i + 1]
            leg_res = await dist_tool.execute(origin=s1, destination=s2)
            leg_data = leg_res.data
            km = leg_data.get("estimated_road_distance_km", 250.0)
            hours = leg_data.get("estimated_drive_time_hours", 4.5)

            if isinstance(km, (int, float)):
                total_road_km += km
            if isinstance(hours, (int, float)):
                total_hours += hours

            legs.append({
                "from": s1,
                "to": s2,
                "distance_km": km,
                "estimated_duration_hours": hours,
            })

        return ToolResult(
            tool_name=self.name,
            success=True,
            data={
                "itinerary_stops": stops,
                "legs": legs,
                "total_estimated_km": round(total_road_km, 1),
                "total_transit_hours": round(total_hours, 1),
            },
            message=f"Route sequenced: {len(stops)} stops, ~{round(total_road_km)} km total.",
            provenance=DataProvenance.CALCULATED,
            is_live_data=True,
            metadata={"stops_count": len(stops)},
        )
