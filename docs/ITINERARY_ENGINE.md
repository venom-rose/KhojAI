# KHOJAI Deterministic Itinerary Generation Engine

## Overview

The **KHOJAI Itinerary Generation Engine** ensures that travel plans are never generated blindly by LLMs. Instead of allowing generative models to invent impossible travel times, hallucinate non-existent road connections, or fabricate lodging rates, KHOJAI uses a **deterministic constraint-satisfaction engine** (`backend/app/travel/services/itinerary_engine.py`).

The deterministic engine algorithmically calculates distances, groups sights into coherent spatial clusters, sequences daily activities, verifies operating hours, scales budgets, preserves unhurried leisure buffers, and generates transparent cost breakdowns. The LLM is then employed strictly to transform this structured, geographically grounded itinerary into an authentic, conversational narrative.

---

## Architecture: Hybrid Deterministic Engine + LLM Narrative

```
User Query / AI Agent Tool Call
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Traveler Inputs (10 Dimensions)             │
│  destination, start_date, end_date, budget, traveler_count, │
│  interests, travel_style, hotel_pref, activity_pref, transit│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│         Deterministic Itinerary Generation Engine           │
│ 1. Validate dates & duration bounds                         │
│ 2. Retrieve destination profile from local DB               │
│ 3. Retrieve & score attractions by user interests           │
│ 4. Retrieve matching cultural activities & workshops        │
│ 5. Retrieve verified hotels by stay type & price tier       │
│ 6. Retrieve transportation hubs & local connectivity        │
│ 7. Calculate Haversine distances + road transit factor      │
│ 8. Group geographically related places (spatial clusters)   │
│ 9. Avoid impossible schedules (≤7.5h daily activity cap)    │
│ 10. Consider opening hours & chronological slot sequencing  │
│ 11. Scale lodging, transit, and meals to budget tier        │
│ 12. Build Day 1..N Morning, Afternoon, Evening slots        │
│ 13. Guarantee unhurried leisure buffers (≥45-75m per slot)  │
│ 14. Produce itemized cost breakdown with 10% contingency    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 StructuredTripItinerary JSON                │
│    (Hierarchical schema: Trip -> Summary, Days, Costs)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 LLM Conversational Synthesis                │
│  - Converts verified schedule into rich narrative           │
│  - Preserves exact computed distances, times, and prices    │
│  - Emphasizes culinary suggestions & cultural etiquette     │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Input Dimensions

The engine accepts 10 structured input parameters via `ItineraryEngineInput` (`backend/app/travel/schemas/itinerary_engine.py`):

| Parameter | Type | Default | Description |
|---|---|---|---|
| `destination` | `str` | *Required* | Target region, city, or district (e.g. `'Jaipur'`, `'Rajasthan'`, `'Spiti'`). |
| `start_date` | `Optional[str]` | `None` | Trip start date in ISO format (`YYYY-MM-DD`). |
| `end_date` | `Optional[str]` | `None` | Trip end date in ISO format (`YYYY-MM-DD`). |
| `duration_days` | `Optional[int]` | `None` | Explicit trip duration in days (used when calendar dates are omitted). |
| `budget` | `str` | `'moderate'` | Budget tier (`'budget'`, `'moderate'`, `'luxury'`) or target currency amount. |
| `traveler_count` | `int` | `1` | Number of travelers (scales room inventory, dining allowances, admissions). |
| `interests` | `List[str]` | `[]` | Traveler preferences (e.g. `['heritage', 'crafts', 'food', 'nature', 'monuments']`). |
| `travel_style` | `str` | `'slow travel'` | Pacing philosophy (`'slow travel'`, `'relaxed'`, `'moderate'`, `'adventure'`). |
| `hotel_preference` | `str` | `'boutique homestay'` | Lodging category (`'boutique homestay'`, `'heritage haveli'`, `'eco-lodge'`). |
| `activity_preferences`| `List[str]` | `[]` | Activity types (`['walking tour', 'cooking workshop', 'river boat']`). |
| `transport_preferences`| `str` | `'private cab / train'`| Commute mode (`'private cab'`, `'auto-rickshaw'`, `'train/public'`). |

---

## 2. The 17 Algorithmic Steps

1. **Date Validation**:
   - Parses `start_date` and `end_date` against `%Y-%m-%d`.
   - Asserts that $end\_date \ge start\_date$; raises descriptive `ValueError` on inverted ranges.
   - Handles missing dates cleanly using current seasonal defaults.

2. **Trip Duration Determination**:
   - Calculates duration: $duration = (end\_date - start\_date) + 1$.
   - Enforces realistic bounds ($1 \le duration \le 14$ days) to prevent impossible micro-trips or marathon itineraries.
   - Generates sequential calendar date strings for every day.

3. **Destination Information Retrieval**:
   - Queries the local database `Destination` table for verified coordinates, state, region, best season, trust score, and editorial description.
   - Falls back gracefully to curated regional index or geographic centroid.

4. **Attractions Retrieval**:
   - Queries verified `Attraction` POIs with coordinates, entry fees (`entry_fee`), operating timings (`timings`), and recommended duration (`recommended_duration_mins`).

5. **Activities Retrieval**:
   - Queries verified experiential `Activity` records matching `activity_preferences` with durations and pricing estimates.

6. **Hotels Retrieval**:
   - Queries `Hotel` matching destination, `hotel_preference`, and budget level.
   - Safely parses numeric rates from string ranges (e.g. `"₹1,500 – ₹2,500"`).

7. **Transportation Information Retrieval**:
   - Queries `TransportationOption` and `Airport` tables for nearest hubs, local commute tips, and transfer durations.

8. **Approximate Distance & Drive Time Calculation**:
   - Calculates geodesic point-to-point distances using the Haversine formula:
     $$d = 2r \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \text{lat}}{2}\right) + \cos(\text{lat}_1)\cos(\text{lat}_2)\sin^2\left(\frac{\Delta \text{lon}}{2}\right)}\right)$$
   - Applies an Indian road transit multiplier ($\times 1.35$) and realistic city speeds (approx 2.5 minutes per km in city traffic).

9. **Geographic Clustering**:
   - Groups sights by spatial proximity so that every day focuses on a distinct neighborhood cluster (e.g. "Old Walled City", "Aravalli Ridge", "Lake Quarter") without criss-crossing.

10. **Avoid Impossible Schedules**:
    - Caps total daily scheduled activity time to $\le 6.5 - 7.5$ hours.
    - Limits scheduled visits to 3–4 items per day (Morning 1–2, Afternoon 1, Evening 1).

11. **Opening Hours Consideration**:
    - Ensures morning attractions open early ($\le$ 09:30 AM).
    - Afternoon slots accommodate cultural museums/palaces open through 05:00 PM.
    - Evening activities match sunset, night markets, or cultural performances (05:30 PM – 08:30 PM).

12. **User Interests Consideration**:
    - Scores and weights attractions using multi-field keyword matching:
      $$\text{Score} = 4 \times (\text{Category Match}) + 3 \times (\text{Tag Match}) + 1 \times (\text{Description Match})$$
    - Sorts POIs so traveler interests (e.g. crafts, temples, nature) dominate daily selections.

13. **Budget Consideration**:
    - Scales lodging rates: Budget (~₹1,400/night), Moderate (~₹3,200/night), Luxury (~₹8,500/night).
    - Scales daily food allowances: Budget (₹650/day), Moderate (₹1,300/day), Luxury (₹2,800/day).
    - Scales local transit: Budget (₹800/day auto/bus), Moderate (₹1,500/day cab), Luxury (₹3,000/day private car).

14. **Day-by-Day Activity Creation**:
    - Assembles explicit, non-overlapping `morning`, `afternoon`, and `evening` schedule slots.

15. **Reasonable Free Time Buffers**:
    - Guarantees built-in leisure time buffers ($\ge 45-60$ minutes in the morning, $\ge 60$ minutes in the afternoon, $\ge 60-75$ minutes in the evening).

16. **Estimated Cost Breakdown**:
    - Itemizes Accommodation, Activities/Admissions, Local Transit, Dining, and a 10% contingency buffer:
      $$\text{Total} = (\text{Lodging} + \text{Activities} + \text{Transit} + \text{Dining}) \times 1.10$$
    - Outputs both total estimated cost and per-person cost.

17. **Structured Output Container**:
    - Serializes into `StructuredTripItinerary` containing complete day plans, transit details, and curator notes.

---

## 3. Hierarchical Output Schema

```
Trip
├── Summary
├── Destination
├── Duration
├── Budget
├── Estimated Cost
│    ├── accommodation_inr
│    ├── activities_and_admission_inr
│    ├── local_transport_inr
│    ├── food_and_dining_inr
│    ├── contingency_inr
│    ├── total_estimated_inr
│    └── per_person_inr
├── Day 1
│    ├── neighborhood_cluster
│    ├── day_hotel
│    ├── transit_totals (km & minutes)
│    ├── Morning
│    │    ├── activities [start_time, end_time, title, place, fee, hours, transit]
│    │    ├── free_time_minutes
│    │    └── culinary_recommendation
│    ├── Afternoon
│    │    ├── activities [...]
│    │    ├── free_time_minutes
│    │    └── culinary_recommendation
│    └── Evening
│         ├── activities [...]
│         ├── free_time_minutes
│         └── culinary_recommendation
├── Day 2
│    ├── Morning
│    ├── Afternoon
│    └── Evening
└── ...
```

---

## 4. AI Agent Tool Calling Integration

The itinerary engine is registered as `create_itinerary` in `default_tool_registry` (`backend/app/ai/tools/trip_tools.py`).

### Agent Tool Invocation Example:
```python
from backend.app.ai.tools.trip_tools import CreateItineraryTool

tool = CreateItineraryTool()
result = await tool.execute(
    destination="Jaipur",
    days=3,
    start_date="2026-11-01",
    end_date="2026-11-03",
    budget="moderate",
    traveler_count=2,
    interests=["heritage", "crafts"],
    travel_style="slow travel",
    hotel_preference="heritage haveli",
    activity_preferences=["walking tour", "block printing"],
    transport_preferences="private cab",
)

print("Status:", result.success)
print("Provenance:", result.provenance) # DataProvenance.CALCULATED
print("Itinerary JSON:", result.data)
```

### Context Synthesis & LLM Narrative Transformation:
When the agent executes `create_itinerary`, the `ContextBuilder` formats the structured output and injects the following directive into the LLM system prompt:
> *"When a structured itinerary was generated by `create_itinerary`: Present the trip hierarchically: Executive Summary, Day-by-Day Morning/Afternoon/Evening highlights, neighborhood clusters, and the itemized cost breakdown. Faithfully respect the deterministic transit distances, drive times, and pricing generated by the engine—do not invent conflicting figures. Emphasize the built-in free time buffers and authentic regional culinary recommendations."*

---

## 5. Verification & Testing

Validated in `backend/tests/test_itinerary_engine.py`:
- `test_haversine_distance_calculation`: Geodesic coordinate distance accuracy.
- `test_date_validation_and_duration`: Chronological validation, inverted date rejection, format error raising, duration bounds.
- `test_itinerary_generation_structure_and_slots`: Hierarchical DayPlan structure with Morning, Afternoon, Evening slots.
- `test_itinerary_geographic_clustering_and_no_impossible_schedule`: Spatial clustering and $\le 7.5$ hours daily activity limit.
- `test_itinerary_cost_estimation_math`: Mathematical precision of itemized breakdown and 10% contingency.
- `test_itinerary_budget_tiers_scaling`: Cost scaling across `budget` vs `luxury` tiers.
- `test_interest_and_activity_preference_prioritization`: Interest scoring and craft/textile keyword boost.
- `test_transportation_retrieval_and_guidance`: Transit options and airport hub lookup.
- `test_opening_hours_and_time_slot_alignment`: Chronological slot timing and opening hours alignment.
- `test_create_itinerary_tool_with_all_10_inputs`: End-to-end tool execution with all 10 user prompt parameters.

**Test Suite Status**: 10/10 engine tests passing; **138/138 full backend tests passing**.
