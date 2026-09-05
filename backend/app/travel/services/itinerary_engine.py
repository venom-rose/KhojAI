import logging
import math
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, select
from backend.app.database.session import async_session_factory
from backend.app.models import (
    Activity,
    Airport,
    Attraction,
    City,
    Destination,
    Hotel,
    Restaurant,
    TransportationOption,
)
from backend.app.travel.schemas.itinerary_engine import (
    CostBreakdown,
    DayPlan,
    DayScheduleSlot,
    ItineraryEngineInput,
    StructuredTripItinerary,
    TimeSlotActivity,
)

logger = logging.getLogger("khojai.travel.itinerary_engine")


# Haversine distance calculator
def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two coordinate pairs in kilometers."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 2)


# Curated regional knowledge fallback when database records are minimal
REGIONAL_CURATED_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    "jaipur": {
        "coords": (26.9124, 75.7873),
        "state": "Rajasthan",
        "clusters": [
            {
                "name": "Walled Pink City & Royal Quarter",
                "attractions": [
                    {
                        "name": "City Palace Jaipur",
                        "category": "heritage",
                        "fee": 300,
                        "duration": 2.0,
                        "hours": "09:30 AM - 05:00 PM",
                        "coords": (26.9258, 75.8237),
                        "desc": "Splendid blend of Rajasthani and Mughal court architecture with courtyards and private collections.",
                    },
                    {
                        "name": "Jantar Mantar Astronomical Observatory",
                        "category": "heritage",
                        "fee": 200,
                        "duration": 1.5,
                        "hours": "09:00 AM - 05:00 PM",
                        "coords": (26.9248, 75.8246),
                        "desc": "18th-century stone astronomical instruments designed by Sawai Jai Singh II.",
                    },
                    {
                        "name": "Hawa Mahal (Palace of Winds)",
                        "category": "monument",
                        "fee": 100,
                        "duration": 1.0,
                        "hours": "09:00 AM - 05:00 PM",
                        "coords": (26.9239, 75.8267),
                        "desc": "Five-story pink sandstone façade with 953 jharokhas designed for royal court ladies.",
                    },
                ],
                "evening_activity": {
                    "name": "Bapu Bazaar Artisanal Textile Walk",
                    "category": "crafts",
                    "fee": 0,
                    "duration": 2.0,
                    "hours": "10:30 AM - 08:30 PM",
                    "coords": (26.9196, 75.8214),
                    "desc": "Explore traditional hand-block prints, tie-dye leheriya, and handcrafted leather mojari slippers.",
                },
                "dining": "Laxmi Mishthan Bhandar (LMB) for authentic kachori and ghewar.",
            },
            {
                "name": "Northern Aravalli Forts Corridor",
                "attractions": [
                    {
                        "name": "Amber Fort & Palace",
                        "category": "heritage",
                        "fee": 500,
                        "duration": 2.5,
                        "hours": "09:00 AM - 05:30 PM",
                        "coords": (26.9855, 75.8513),
                        "desc": "Monumental hilltop citadel with Sheesh Mahal (hall of mirrors) overlooking Maota Lake.",
                    },
                    {
                        "name": "Panna Meena ka Kund Stepwell",
                        "category": "monument",
                        "fee": 0,
                        "duration": 1.0,
                        "hours": "07:00 AM - 06:00 PM",
                        "coords": (26.9930, 75.8538),
                        "desc": "16th-century geometric symmetrical stepwell engineered for water conservation and community gatherings.",
                    },
                    {
                        "name": "Anokhi Museum of Hand Printing",
                        "category": "crafts",
                        "fee": 80,
                        "duration": 1.5,
                        "hours": "10:30 AM - 05:00 PM",
                        "coords": (26.9922, 75.8501),
                        "desc": "Restored heritage haveli dedicated to the preservation of ancient wooden block carving and natural dyes.",
                    },
                ],
                "evening_activity": {
                    "name": "Nahargarh Fort Sunset Viewpoint",
                    "category": "nature",
                    "fee": 100,
                    "duration": 2.0,
                    "hours": "10:00 AM - 06:30 PM",
                    "coords": (26.9372, 75.8155),
                    "desc": "Sunset vantage point along the rugged Aravalli ridge gazing over the entire Pink City skyline.",
                },
                "dining": "Padao Open-air Cafe atop Nahargarh ridge or 1135 AD inside Amber.",
            },
            {
                "name": "Southern Heritage & Craft Quarters",
                "attractions": [
                    {
                        "name": "Albert Hall Central Museum",
                        "category": "heritage",
                        "fee": 150,
                        "duration": 1.5,
                        "hours": "09:00 AM - 05:00 PM",
                        "coords": (26.9116, 75.8195),
                        "desc": "Indo-Saracenic museum housing royal weaponry, carpets, pottery, and miniature paintings.",
                    },
                    {
                        "name": "Galtaji Temple (Monkey Temple & Sacred Kunds)",
                        "category": "spiritual",
                        "fee": 0,
                        "duration": 2.0,
                        "hours": "06:00 AM - 07:00 PM",
                        "coords": (26.9168, 75.8576),
                        "desc": "Ancient sacred pavilion complex tucked between mountain chasms with perennial natural springs.",
                    },
                ],
                "evening_activity": {
                    "name": "Sanganer Blue Pottery & Handmade Paper Studios",
                    "category": "crafts",
                    "fee": 0,
                    "duration": 2.0,
                    "hours": "10:00 AM - 06:00 PM",
                    "coords": (26.8188, 75.7686),
                    "desc": "Visit master artisans crafting traditional blue pottery with quartz and plant gum glazes.",
                },
                "dining": "Rawat Mishthan Bhandar for crisp Pyaaz Kachoris and fresh lassi.",
            },
        ],
    },
    "rajasthan": {
        "coords": (26.9124, 75.7873),
        "state": "Rajasthan",
        "clusters": [
            {
                "name": "Jaipur - The Pink City Citadel",
                "attractions": [
                    {
                        "name": "Amber Fort & Palace",
                        "category": "heritage",
                        "fee": 500,
                        "duration": 2.5,
                        "hours": "09:00 AM - 05:30 PM",
                        "coords": (26.9855, 75.8513),
                        "desc": "Massive hill citadel overlooking Maota Lake with pristine mirror mosaics.",
                    },
                    {
                        "name": "City Palace & Jantar Mantar",
                        "category": "heritage",
                        "fee": 300,
                        "duration": 2.0,
                        "hours": "09:30 AM - 05:00 PM",
                        "coords": (26.9258, 75.8237),
                        "desc": "Royal residential courtyards and world-heritage astronomical instruments.",
                    },
                ],
                "evening_activity": {
                    "name": "Old Bazaars & Heritage Walk",
                    "category": "crafts",
                    "fee": 0,
                    "duration": 2.0,
                    "hours": "11:00 AM - 08:30 PM",
                    "coords": (26.9239, 75.8267),
                    "desc": "Stroll past spice stalls and artisan block-printing ateliers.",
                },
                "dining": "Authentic Dal Baati Churma at a verified heritage haveli.",
            },
            {
                "name": "Jodhpur - The Blue City & Mehrangarh",
                "attractions": [
                    {
                        "name": "Mehrangarh Fort",
                        "category": "heritage",
                        "fee": 400,
                        "duration": 2.5,
                        "hours": "09:00 AM - 05:00 PM",
                        "coords": (26.2978, 73.0185),
                        "desc": "Towering 400-foot cliffside fortress with preserved royal palanquins and armory.",
                    },
                    {
                        "name": "Jaswant Thada Cenotaphs",
                        "category": "monument",
                        "fee": 50,
                        "duration": 1.0,
                        "hours": "09:00 AM - 05:00 PM",
                        "coords": (26.3039, 73.0239),
                        "desc": "Delicate white marble memorial pavilion set beside a serene lake.",
                    },
                ],
                "evening_activity": {
                    "name": "Brahmapuri Blue Quarter Walking Tour",
                    "category": "heritage",
                    "fee": 0,
                    "duration": 1.5,
                    "hours": "04:30 PM - 07:00 PM",
                    "coords": (26.2945, 73.0160),
                    "desc": "Narrow indigo-painted alleyways with friendly neighborhood tea corners.",
                },
                "dining": "Shahi Samosa and Makhaniya Lassi near the historic Clock Tower.",
            },
            {
                "name": "Udaipur - City of Lakes & Royal Havelis",
                "attractions": [
                    {
                        "name": "Udaipur City Palace Complex",
                        "category": "heritage",
                        "fee": 350,
                        "duration": 2.5,
                        "hours": "09:00 AM - 05:30 PM",
                        "coords": (24.5764, 73.6835),
                        "desc": "Rajasthan's largest royal palace complex overlooking Lake Pichola.",
                    },
                    {
                        "name": "Jagdish Temple & Old City Ghats",
                        "category": "spiritual",
                        "fee": 0,
                        "duration": 1.0,
                        "hours": "05:00 AM - 09:00 PM",
                        "coords": (24.5796, 73.6845),
                        "desc": "1651 AD carved stone temple dedicated to Lord Vishnu.",
                    },
                ],
                "evening_activity": {
                    "name": "Lake Pichola Sunset Boat Ride",
                    "category": "nature",
                    "fee": 450,
                    "duration": 1.5,
                    "hours": "04:30 PM - 06:30 PM",
                    "coords": (24.5744, 73.6789),
                    "desc": "Quiet water journey past Lake Palace and Jagmandir Island as lights reflect on the water.",
                },
                "dining": "Ambrai Restaurant at Amet Haveli overlooking the illuminated City Palace.",
            },
        ],
    },
}


class ItineraryGenerationEngine:
    """Deterministic, constraint-satisfying travel itinerary generation engine."""

    # 1. Validate Dates & Determine Duration
    @staticmethod
    def validate_and_compute_duration(
        start_date_str: Optional[str],
        end_date_str: Optional[str],
        duration_days: Optional[int],
    ) -> Tuple[int, Optional[date], Optional[date], List[str]]:
        """Validate date inputs, compute trip duration, and build day date strings."""
        parsed_start: Optional[date] = None
        parsed_end: Optional[date] = None

        if start_date_str:
            try:
                parsed_start = datetime.strptime(start_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Invalid start_date format '{start_date_str}'. Use YYYY-MM-DD.")

        if end_date_str:
            try:
                parsed_end = datetime.strptime(end_date_str.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise ValueError(f"Invalid end_date format '{end_date_str}'. Use YYYY-MM-DD.")

        if parsed_start and parsed_end:
            if parsed_end < parsed_start:
                raise ValueError(f"end_date ({parsed_end}) cannot be earlier than start_date ({parsed_start}).")
            duration = (parsed_end - parsed_start).days + 1
        elif duration_days:
            duration = duration_days
            if parsed_start and not parsed_end:
                parsed_end = parsed_start + timedelta(days=duration - 1)
        else:
            duration = 3  # standard sensible default

        # Clamp duration to realistic bounds
        clamped_duration = max(1, min(14, duration))

        # Generate date labels
        date_strings: List[str] = []
        base_date = parsed_start or date.today()
        for i in range(clamped_duration):
            d = base_date + timedelta(days=i)
            date_strings.append(d.strftime("%Y-%m-%d"))

        return clamped_duration, parsed_start, parsed_end, date_strings

    # 2. Retrieve Destination Information
    @staticmethod
    async def retrieve_destination(dest_query: str) -> Dict[str, Any]:
        """Fetch destination profile from local DB or curated fallback."""
        clean_name = dest_query.strip().lower()

        async with async_session_factory() as session:
            stmt = select(Destination).where(
                Destination.is_deleted.is_(False),
                or_(
                    Destination.name.ilike(f"%{clean_name}%"),
                    Destination.state.ilike(f"%{clean_name}%"),
                ),
            )
            res = await session.execute(stmt)
            dest = res.scalars().first()

            if dest:
                return {
                    "id": str(dest.id),
                    "name": dest.name,
                    "state": dest.state,
                    "country": dest.country,
                    "description": dest.description or dest.short_description,
                    "latitude": float(dest.latitude) if dest.latitude else 26.9124,
                    "longitude": float(dest.longitude) if dest.longitude else 75.7873,
                    "budget_tier": dest.budget_tier or "moderate",
                    "tags": dest.tags or [],
                }

        # Curated fallback
        for key, info in REGIONAL_CURATED_KNOWLEDGE.items():
            if key in clean_name:
                coords = info["coords"]
                return {
                    "id": f"dest-{key}",
                    "name": dest_query.title(),
                    "state": info["state"],
                    "country": "India",
                    "description": f"Curated cultural and heritage region of {dest_query.title()}.",
                    "latitude": coords[0],
                    "longitude": coords[1],
                    "budget_tier": "moderate",
                    "tags": ["heritage", "culture", "slow travel"],
                }

        return {
            "id": "dest-general",
            "name": dest_query.title(),
            "state": "India",
            "country": "India",
            "description": f"Enriching travel journey across {dest_query.title()}.",
            "latitude": 26.9124,
            "longitude": 75.7873,
            "budget_tier": "moderate",
            "tags": ["culture", "heritage"],
        }

    # 3. Retrieve POIs & Group Geographically
    @staticmethod
    async def retrieve_and_cluster_pois(
        destination_name: str,
        interests: List[str],
        duration_days: int,
    ) -> List[Dict[str, Any]]:
        """Retrieve attractions and group them into cohesive spatial clusters for each day."""
        clean_name = destination_name.lower()

        # Check curated knowledge base clusters first
        for key, data in REGIONAL_CURATED_KNOWLEDGE.items():
            if key in clean_name:
                clusters = data["clusters"]
                # Repeat/cycle or slice clusters to match duration
                out_clusters = []
                for i in range(duration_days):
                    base_cluster = clusters[i % len(clusters)]
                    out_clusters.append({
                        "name": f"{base_cluster['name']} (Day {i+1})",
                        "attractions": base_cluster["attractions"],
                        "evening_activity": base_cluster.get("evening_activity"),
                        "dining": base_cluster.get("dining", "Verified traditional restaurant"),
                    })
                return out_clusters

        # Query database attractions
        async with async_session_factory() as session:
            stmt = select(Attraction).join(Attraction.city, isouter=True).where(
                or_(
                    Attraction.name.ilike(f"%{clean_name}%"),
                    City.name.ilike(f"%{clean_name}%"),
                )
            ).limit(15)
            res = await session.execute(stmt)
            db_attractions = res.scalars().all()

        if db_attractions:
            # Group into day slices of 2-3 attractions per day
            clusters = []
            per_day = max(2, math.ceil(len(db_attractions) / duration_days))
            for i in range(duration_days):
                slice_start = (i * per_day) % len(db_attractions)
                day_atts = db_attractions[slice_start : slice_start + per_day]
                if not day_atts:
                    day_atts = db_attractions[:2]

                cluster_atts = [
                    {
                        "name": a.name,
                        "category": a.category or "heritage",
                        "fee": float(a.admission_fee) if a.admission_fee else 150.0,
                        "duration": float(a.estimated_duration_hours) if a.estimated_duration_hours else 2.0,
                        "hours": a.opening_hours or "09:00 AM - 05:00 PM",
                        "coords": (float(a.latitude), float(a.longitude)) if a.latitude and a.longitude else (26.9124, 75.7873),
                        "desc": a.description or f"Historic attraction in {destination_name}.",
                    }
                    for a in day_atts
                ]

                clusters.append({
                    "name": f"{destination_name.title()} Cultural Sector {i+1}",
                    "attractions": cluster_atts,
                    "evening_activity": {
                        "name": f"{destination_name.title()} Evening Heritage Promenade",
                        "category": "leisure",
                        "fee": 0,
                        "duration": 1.5,
                        "hours": "05:00 PM - 08:00 PM",
                        "coords": cluster_atts[0]["coords"] if cluster_atts else (26.9124, 75.7873),
                        "desc": "Leisurely sunset stroll exploring local markets and community ambiance.",
                    },
                    "dining": f"Renowned regional dining in {destination_name}.",
                })
            return clusters

        # Universal fallback cluster
        universal_clusters = []
        for i in range(duration_days):
            universal_clusters.append({
                "name": f"{destination_name.title()} Exploration Cluster {i+1}",
                "attractions": [
                    {
                        "name": f"Historic Monument of {destination_name}",
                        "category": "heritage",
                        "fee": 200,
                        "duration": 2.0,
                        "hours": "09:30 AM - 05:00 PM",
                        "coords": (26.9124, 75.7873),
                        "desc": f"Prominent historic site showcasing traditional architecture of {destination_name}.",
                    },
                    {
                        "name": f"{destination_name} Artisanal Craft Center",
                        "category": "crafts",
                        "fee": 50,
                        "duration": 1.5,
                        "hours": "10:00 AM - 05:30 PM",
                        "coords": (26.9200, 75.7950),
                        "desc": "Community workshop demonstrating regional handcrafted textiles and pottery.",
                    },
                ],
                "evening_activity": {
                    "name": f"{destination_name} Sunset Viewpoint",
                    "category": "nature",
                    "fee": 0,
                    "duration": 1.5,
                    "hours": "05:30 PM - 07:30 PM",
                    "coords": (26.9300, 75.8050),
                    "desc": "Tranquil sunset overlook offering panoramic vistas.",
                },
                "dining": "Local family-run dhaba serving authentic home-style thalis.",
            })
        return universal_clusters

    # 4. Retrieve Accommodations
    @staticmethod
    async def retrieve_hotel(
        destination_name: str,
        hotel_preference: str,
        budget_tier: str,
    ) -> Dict[str, Any]:
        """Fetch recommended lodging matching preferences and price tier."""
        clean_name = destination_name.lower()
        async with async_session_factory() as session:
            stmt = select(Hotel).where(
                or_(
                    Hotel.name.ilike(f"%{clean_name}%"),
                    Hotel.address.ilike(f"%{clean_name}%"),
                )
            ).limit(1)
            res = await session.execute(stmt)
            db_hotel = res.scalars().first()

            if db_hotel:
                rate = float(db_hotel.price_per_night) if db_hotel.price_per_night else 3200.0
                return {
                    "name": db_hotel.name,
                    "stay_type": db_hotel.stay_type or "Boutique Heritage Stay",
                    "nightly_rate_inr": rate,
                    "rating": float(db_hotel.rating) if db_hotel.rating else 4.5,
                    "amenities": db_hotel.amenities or ["WiFi", "Breakfast", "Heritage Architecture"],
                    "address": db_hotel.address or f"Central {destination_name.title()}",
                }

        # Pricing benchmark by tier
        tier_rates = {
            "budget": 1400.0,
            "moderate": 3200.0,
            "luxury": 8500.0,
        }
        normalized_tier = "moderate"
        for t in ["budget", "moderate", "luxury"]:
            if t in budget_tier.lower() or t in hotel_preference.lower():
                normalized_tier = t
                break

        return {
            "name": f"{destination_name.title()} Heritage Homestay",
            "stay_type": hotel_preference.title() if hotel_preference else "Boutique Homestay",
            "nightly_rate_inr": tier_rates[normalized_tier],
            "rating": 4.7,
            "amenities": ["Fresh Farm Breakfast", "Courtyard", "Local Guides"],
            "address": f"Heritage Quarter, {destination_name.title()}",
        }

    # 5. Build Day Plan with Slots, Free Time, & Transit
    @staticmethod
    def construct_day_plan(
        day_num: int,
        date_str: Optional[str],
        cluster: Dict[str, Any],
        hotel: Dict[str, Any],
        travel_style: str,
    ) -> DayPlan:
        """Assemble morning, afternoon, and evening schedule slots with built-in unhurried buffers."""
        atts = cluster["attractions"]
        att1 = atts[0] if len(atts) > 0 else None
        att2 = atts[1] if len(atts) > 1 else None
        evening = cluster.get("evening_activity")

        day_transit_km = 0.0
        day_transit_min = 0

        # Morning Slot: 09:00 AM - 01:00 PM
        morning_activities: List[TimeSlotActivity] = []
        if att1:
            c1 = att1["coords"]
            h_coords = (c1[0] - 0.02, c1[1] - 0.02)  # approximate hotel location
            dist = haversine_distance_km(h_coords[0], h_coords[1], c1[0], c1[1])
            t_min = max(15, int(dist * 2.5))
            day_transit_km += dist
            day_transit_min += t_min

            morning_activities.append(
                TimeSlotActivity(
                    title=att1["name"],
                    place_name=att1["name"],
                    category=att1.get("category", "heritage"),
                    start_time="09:30 AM",
                    end_time="12:00 PM",
                    duration_hours=att1.get("duration", 2.0),
                    description=att1.get("desc", ""),
                    cost_estimate_inr=float(att1.get("fee", 100)),
                    latitude=c1[0],
                    longitude=c1[1],
                    opening_hours=att1.get("hours"),
                    transit_from_previous={
                        "from": "Hotel",
                        "distance_km": dist,
                        "drive_minutes": t_min,
                        "mode": "Auto-rickshaw / Cab",
                    },
                )
            )

        morning_slot = DayScheduleSlot(
            time_window="09:00 AM - 01:00 PM",
            theme=f"Morning Exploration: {att1['name'] if att1 else 'Cultural Discovery'}",
            activities=morning_activities,
            free_time_minutes=60,
            culinary_recommendation="Traditional morning chai and local savory kachoris.",
        )

        # Afternoon Slot: 02:00 PM - 05:30 PM (after 1-hour relaxed lunch)
        afternoon_activities: List[TimeSlotActivity] = []
        if att2:
            c2 = att2["coords"]
            prev_coords = att1["coords"] if att1 else c2
            dist = haversine_distance_km(prev_coords[0], prev_coords[1], c2[0], c2[1])
            t_min = max(10, int(dist * 2.5))
            day_transit_km += dist
            day_transit_min += t_min

            afternoon_activities.append(
                TimeSlotActivity(
                    title=att2["name"],
                    place_name=att2["name"],
                    category=att2.get("category", "heritage"),
                    start_time="02:30 PM",
                    end_time="04:30 PM",
                    duration_hours=att2.get("duration", 1.5),
                    description=att2.get("desc", ""),
                    cost_estimate_inr=float(att2.get("fee", 50)),
                    latitude=c2[0],
                    longitude=c2[1],
                    opening_hours=att2.get("hours"),
                    transit_from_previous={
                        "from": att1["name"] if att1 else "Lunch Stop",
                        "distance_km": dist,
                        "drive_minutes": t_min,
                        "mode": "Short Transit",
                    },
                )
            )

        afternoon_slot = DayScheduleSlot(
            time_window="01:00 PM - 05:30 PM",
            theme=f"Afternoon Immersion: {att2['name'] if att2 else 'Artisanal Experience'}",
            activities=afternoon_activities,
            free_time_minutes=60,
            culinary_recommendation=cluster.get("dining", "Regional thali at a verified local courtyard."),
        )

        # Evening Slot: 06:00 PM - 09:30 PM
        evening_activities: List[TimeSlotActivity] = []
        if evening:
            ec = evening.get("coords", (26.9124, 75.7873))
            dist = 3.5
            t_min = 20
            day_transit_km += dist
            day_transit_min += t_min

            evening_activities.append(
                TimeSlotActivity(
                    title=evening["name"],
                    place_name=evening["name"],
                    category=evening.get("category", "leisure"),
                    start_time="06:00 PM",
                    end_time="07:45 PM",
                    duration_hours=evening.get("duration", 1.5),
                    description=evening.get("desc", ""),
                    cost_estimate_inr=float(evening.get("fee", 0)),
                    latitude=ec[0],
                    longitude=ec[1],
                    opening_hours=evening.get("hours"),
                    transit_from_previous={
                        "from": "Afternoon Hub",
                        "distance_km": dist,
                        "drive_minutes": t_min,
                        "mode": "Evening Walk / Local Cab",
                    },
                )
            )

        evening_slot = DayScheduleSlot(
            time_window="06:00 PM - 09:30 PM",
            theme=f"Evening Ambiance: {evening['name'] if evening else 'Sunset & Night Market'}",
            activities=evening_activities,
            free_time_minutes=75,
            culinary_recommendation="Dinner featuring slow-cooked regional delicacies and sweets.",
        )

        return DayPlan(
            day_number=day_num,
            date_str=date_str,
            title=f"Day {day_num}: {cluster['name']}",
            neighborhood_cluster=cluster["name"],
            morning=morning_slot,
            afternoon=afternoon_slot,
            evening=evening_slot,
            day_hotel=hotel,
            day_total_transit_km=round(day_transit_km, 1),
            day_total_transit_minutes=day_transit_min,
        )

    # 6. Calculate Budget & Itemized Costs
    @staticmethod
    def calculate_cost_breakdown(
        duration_days: int,
        traveler_count: int,
        hotel_nightly_rate: float,
        days_plans: List[DayPlan],
        budget_tier: str,
    ) -> CostBreakdown:
        """Calculate transparent, itemized travel expenses for all travelers."""
        rooms_needed = math.ceil(traveler_count / 2)
        total_nights = max(1, duration_days - 1 if duration_days > 1 else 1)
        accommodation_total = round(hotel_nightly_rate * total_nights * rooms_needed, 2)

        # Sum admission fees across all days
        admissions_per_person = 0.0
        for day in days_plans:
            for slot in [day.morning, day.afternoon, day.evening]:
                for act in slot.activities:
                    admissions_per_person += act.cost_estimate_inr
        activities_total = round(admissions_per_person * traveler_count, 2)

        # Local transit estimate (approx ₹750 - ₹1200 / day for auto/cab)
        daily_transit_rate = 900.0 if "budget" in budget_tier.lower() else 1500.0
        local_transport_total = round(daily_transit_rate * duration_days, 2)

        # Food & dining estimate per traveler per day (₹600 - ₹1500/day)
        daily_food_pp = 700.0 if "budget" in budget_tier.lower() else (1200.0 if "moderate" in budget_tier.lower() else 2500.0)
        food_total = round(daily_food_pp * duration_days * traveler_count, 2)

        # 10% contingency buffer
        subtotal = accommodation_total + activities_total + local_transport_total + food_total
        contingency = round(subtotal * 0.10, 2)
        grand_total = round(subtotal + contingency, 2)
        per_person = round(grand_total / traveler_count, 2)

        return CostBreakdown(
            accommodation_inr=accommodation_total,
            activities_and_admission_inr=activities_total,
            local_transport_inr=local_transport_total,
            food_and_dining_inr=food_total,
            contingency_inr=contingency,
            total_estimated_inr=grand_total,
            per_person_inr=per_person,
            currency="INR",
        )

    # 7. Master Entry Point: Generate Itinerary
    async def generate(self, payload: ItineraryEngineInput) -> StructuredTripItinerary:
        """Generate a complete, deterministic, geographically clustered travel itinerary."""
        # 1. Validate dates & duration
        duration_days, start_d, end_d, date_strings = self.validate_and_compute_duration(
            start_date_str=payload.start_date,
            end_date_str=payload.end_date,
            duration_days=payload.duration_days,
        )

        # 2. Retrieve destination
        destination_data = await self.retrieve_destination(payload.destination)

        # 3. Retrieve & cluster POIs
        clusters = await self.retrieve_and_cluster_pois(
            destination_name=destination_data["name"],
            interests=payload.interests,
            duration_days=duration_days,
        )

        # 4. Retrieve hotel
        hotel = await self.retrieve_hotel(
            destination_name=destination_data["name"],
            hotel_preference=payload.hotel_preference,
            budget_tier=payload.budget,
        )

        # 5. Build daily schedule
        day_plans: List[DayPlan] = []
        for i in range(duration_days):
            day_plan = self.construct_day_plan(
                day_num=i + 1,
                date_str=date_strings[i] if i < len(date_strings) else None,
                cluster=clusters[i],
                hotel=hotel,
                travel_style=payload.travel_style,
            )
            day_plans.append(day_plan)

        # 6. Compute costs
        costs = self.calculate_cost_breakdown(
            duration_days=duration_days,
            traveler_count=payload.traveler_count,
            hotel_nightly_rate=hotel["nightly_rate_inr"],
            days_plans=day_plans,
            budget_tier=payload.budget,
        )

        # 7. Summary and logistics
        summary = (
            f"An authentic {duration_days}-day journey through {destination_data['name']}, designed for "
            f"{payload.traveler_count} traveler(s) at an unhurried, culturally grounded pace. "
            f"Each day focuses on a distinct geographic neighborhood to avoid unnecessary transit, "
            f"balancing iconic monuments with peaceful craft ateliers, sacred springs, and local culinary heritage."
        )

        transport_guidance = {
            "arrival_hub": f"Reach {destination_data['name']} via direct train or flight.",
            "local_commute": payload.transport_preferences,
            "transit_tip": "For historic quarters with narrow lanes, pre-book registered e-rickshaws or take walking tours to avoid traffic congestion.",
        }

        curator_notes = [
            "Dress respectfully when entering temples or traditional royal pavilions.",
            "Verify opening hours locally on government gazette holidays or festival days.",
            "Carry small cash notes for artisanal markets and street food vendors.",
            "Stay well-hydrated and favor early morning fort visits to beat midday sun.",
        ]

        return StructuredTripItinerary(
            summary=summary,
            destination=destination_data["name"],
            duration_days=duration_days,
            start_date=start_d.strftime("%Y-%m-%d") if start_d else None,
            end_date=end_d.strftime("%Y-%m-%d") if end_d else None,
            traveler_count=payload.traveler_count,
            budget_tier=payload.budget,
            estimated_cost=costs,
            days=day_plans,
            pacing_rating="Unhurried & Immersive",
            transportation_guidance=transport_guidance,
            curator_notes=curator_notes,
        )


# Global singleton instance
itinerary_engine = ItineraryGenerationEngine()
