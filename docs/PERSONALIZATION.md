# KHOJAI Personalization & Recommendation Engine Architecture

## 1. Overview & Core Philosophy

The KHOJAI Personalization Layer delivers deterministic, explainable, and privacy-conscious travel recommendations across five primary travel dimensions:

1. **Destinations** (`Destination`)
2. **Hotels & Accommodations** (`Hotel`)
3. **Experiential Activities** (`Activity`)
4. **Local Eateries & Dining** (`Restaurant`)
5. **Day-by-Day Itineraries** (`Trip`)

Instead of relying on black-box probabilistic heuristics or generating recommendations blindly, KHOJAI scores candidates using a **6-factor explainable recommendation scoring formula**. Each recommendation provides an itemized score breakdown and transparent natural-language justifications that the AI travel agent can explain directly to the user (e.g. *"Recommended because it matches your interest in history and fits your selected budget."*).

---

## 2. Privacy-by-Design Principles

KHOJAI strictly adheres to minimal, privacy-centric data collection:
- **No Unnecessary Sensitive Information**: The engine **never** solicits or stores identity documents (passports, national ID / Aadhaar), financial credentials (card numbers, bank accounts, CVV), health/biometric records, or personal contacts beyond what is strictly necessary for account authentication.
- **Strict Payload Validation**: Any preference update attempt containing forbidden sensitive keys (e.g. `passport`, `aadhaar`, `ssn`, `credit_card`, `bank_account`) is rejected immediately with HTTP 422.
- **User Agency**: Users maintain complete autonomy to view, update, replace, or reset their travel preferences at any time via authenticated REST endpoints.

---

## 3. Data Model: `UserTravelPreference`

Stored as a 1:1 relation with the authenticated `User` entity (`user_travel_preferences` table).

### Schema Specification

| Field | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `preferred_destinations` | `List[str]` | Target destination names or regions | `["Jaipur", "Ziro", "Ladakh"]` |
| `interests` | `List[str]` | High-affinity travel interest tags | `["History", "Nature", "Architecture", "Food"]` |
| `travel_style` | `str` | Primary travel philosophy | `"Cultural"`, `"Adventure"`, `"Slow travel"`, `"Luxury"` |
| `budget_range` | `str` | Standardized budget category | `"budget"`, `"moderate"`, `"luxury"` (mapped to `₹`, `₹₹`, `₹₹₹`) |
| `preferred_accommodation` | `List[str]` | Stay types | `["Homestay", "Heritage Haveli", "Eco-Lodge"]` |
| `preferred_activities` | `List[str]` | Experiential activity preferences | `["Guided Trek", "Cultural Workshop", "Food Walk"]` |
| `food_preferences` | `List[str]` | Cuisine & dietary needs | `["Vegetarian", "Vegan", "Local Traditional"]` |
| `transportation_preferences` | `List[str]` | Preferred transit methods | `["Train", "Flight", "Private Cab"]` |
| `preferred_trip_duration` | `int` | Preferred trip duration in days | `3`, `5`, `7`, `10` |

---

## 4. Recommendation Scoring Engine

### 6-Factor Multiplicative Formula

Every candidate entity is evaluated across 6 dimensions, with each sub-score bounded in $[0.10, 1.00]$:

$$\text{Composite Score} = \left( \prod_{i=1}^6 \text{Factor}_i \right)^{1/6} \times 100$$

$$\text{score} = \left( \text{destination\_match} \times \text{interest\_match} \times \text{budget\_match} \times \text{activity\_match} \times \text{travel\_style\_match} \times \text{historical\_preference} \right)^{1/6} \times 100$$

### Scoring Dimension Criteria

1. **`destination_match`**:
   - Evaluates whether the entity is located within or matches the user's `preferred_destinations` or preferred geographic regions (`0.50` to `1.00`).
2. **`interest_match`**:
   - Calculates semantic keyword overlap between user `interests` and entity tags, category taxonomy, and descriptions (`0.35` to `1.00`).
3. **`budget_match`**:
   - Matches entity price tier (`₹`, `₹₹`, `₹₹₹`) against user `budget_range`.
   - Exact tier match = `1.00`, 1 tier deviation = `0.60`–`0.65`, 2 tiers deviation = `0.30`–`0.40`.
4. **`activity_match`**:
   - Overlap between user `preferred_activities` and entity activity types, offerings, or surrounding experiential trails (`0.60` to `0.95`).
5. **`travel_style_match`**:
   - Evaluates compatibility with user's `travel_style` (e.g., Cultural styles favor living heritage, Adventure styles favor trekking trails, Slow travel favors eco-lodges and village homestays).
6. **`historical_preference`**:
   - Factor based on past trip satisfaction, verified community ratings ($\text{Rating} / 5.0$), and destination trust scores ($\text{TrustScore} / 100.0$).

---

## 5. Explainability Engine

Each scored recommendation dynamically generates a human-readable explanation from the dimensions scoring $\ge 0.80$:

- **Destinations**:
  > *"Recommended because it matches your interest in History, aligns with your preferred region in North India, and fits your selected moderate budget."*
- **Hotels**:
  > *"Recommended because it offers your preferred Homestay accommodation, fits your moderate budget tier, and has high traveler community ratings (4.8★)."*
- **Activities**:
  > *"Recommended because it matches your preferred activity in Cultural Workshop, engages your interest in Heritage, and aligns with your Cultural travel style."*
- **Restaurants**:
  > *"Recommended because it offers dishes matching your Vegetarian preferences, fits your dining budget, and is highly rated (4.7★) for authentic local flavors."*

---

## 6. REST API Reference

### 1. Get Travel Preferences
- **Endpoint**: `GET /api/v1/users/me/travel-preferences`
- **Auth**: Required (`Bearer <token>` or session cookie)
- **Response**:
```json
{
  "id": "7b8e1a2f-...",
  "user_id": "4a1c2d3e-...",
  "preferred_destinations": ["Jaipur", "Ziro"],
  "interests": ["History", "Architecture", "Local food"],
  "travel_style": "Cultural",
  "budget_range": "moderate",
  "preferred_accommodation": ["Heritage Haveli", "Homestay"],
  "preferred_activities": ["Sightseeing", "Guided Trek"],
  "food_preferences": ["Vegetarian", "Local Traditional"],
  "transportation_preferences": ["Train", "Flight"],
  "preferred_trip_duration": 5,
  "budget_preference": "₹₹",
  "preferred_pace": "balanced",
  "travel_styles": ["Cultural", "Slow travel"],
  "dietary_needs": "strictly_vegetarian",
  "fitness_level": "moderate",
  "preferred_stay_types": ["Heritage Haveli", "Homestay"],
  "preferred_regions": ["Rajasthan", "Northeast"]
}
```

### 2. Update Travel Preferences
- **Endpoint**: `PATCH /api/v1/users/me/travel-preferences` (or `PUT`)
- **Auth**: Required
- **Request Body**:
```json
{
  "interests": ["History", "Forts", "Textile Crafts"],
  "travel_style": "Cultural",
  "budget_range": "moderate",
  "preferred_accommodation": ["Heritage Haveli"],
  "preferred_activities": ["Cultural Workshop", "Guided Walking Tour"],
  "food_preferences": ["Vegetarian", "Rajasthani"],
  "preferred_trip_duration": 4
}
```

### 3. Get Personalized Recommendations
- **Endpoint**: `GET /api/v1/travel/recommendations`
- **Parameters**:
  - `category` (optional, default `"all"`): `"all"`, `"destinations"`, `"hotels"`, `"activities"`, `"restaurants"`, `"itineraries"`
  - `destination` (optional): Filter to a specific destination name (e.g. `"Jaipur"`)
  - `limit` (optional, default `10`): Max candidates returned
- **Response**:
```json
[
  {
    "entity_type": "hotel",
    "entity_id": "9c2e4f1a-...",
    "title": "Samode Haveli",
    "score": 87.4,
    "match_breakdown": {
      "destination_match": 0.95,
      "interest_match": 0.85,
      "budget_match": 1.0,
      "activity_match": 0.75,
      "travel_style_match": 0.95,
      "historical_preference": 0.96
    },
    "explanation": "Recommended because it offers your preferred Heritage Haveli accommodation, fits your moderate budget tier, and has high traveler community ratings (4.8★).",
    "details": {
      "stay_type": "Heritage Haveli",
      "price_level": "₹₹",
      "rating": 4.8
    }
  }
]
```

---

## 7. AI Agent & Tool Orchestration

1. **Tool `get_user_preferences`**:
   - Queries `UserTravelPreference` and returns all 9 personalized fields to the AI orchestrator.
2. **Tool `get_personalized_recommendations`**:
   - Runs `PersonalizedRecommendationEngine.get_personalized_recommendations()`, passing candidate scores and explanations directly into LLM synthesis.
3. **Intent Detection & Routing**:
   - Queries like *"What places should I visit based on my preferences?"* or *"Recommend stays for me in Jaipur"* are detected as `RECOMMENDATION_SEARCH` and routed to preference and recommendation tools.
4. **Conversational Synthesis**:
   - The LLM context synthesis explicitly weaves in the generated explanations so the user understands *why* each place or stay was chosen.
