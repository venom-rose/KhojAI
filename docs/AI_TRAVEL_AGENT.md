# KHOJAI AI Travel Agent Architecture

## Overview

KHOJAI has evolved from a passive knowledge retrieval system into an **Autonomous, Tool-Using AI Travel Agent**. Rather than relying purely on pretrained model weights (which can hallucinate live prices, room inventories, opening hours, or dynamic schedules), the agent dynamically detects traveler intent, selects from 17 specialized travel tools, gathers factual data from live external travel APIs and local databases, grounds the context with explicit provenance badges, and generates verified recommendations.

---

## High-Level Orchestration Pipeline

```
User Message
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                      TravelAgent                            │
│                 (Entrypoint & Lifecycle)                    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    IntentDetector                           │
│  - Classifies UserIntent (DESTINATION_DISCOVERY, etc.)     │
│  - Extracts Entities (origins, destinations, days, budget)  │
│  - Predicts Required Tools                                  │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     ToolSelector                            │
│  - Resolves arguments & binds kwargs to tool definitions    │
│  - Enforces dependency ordering                             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 Travel Tools Execution                      │
│  - Concurrent async execution with error isolation          │
│  - Providers: Amadeus, Google Places (New), Local DB        │
│  - Emits ToolResult with DataProvenance & is_live flags     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ContextBuilder                           │
│  - Assembles dialogue history + user preferences            │
│  - Formats grounded tool results for LLM                    │
│  - Injects Anti-Hallucination Disclaimers & Provenance      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLM Provider                           │
│  - GeminiProvider / OpenAIProvider / LocalProvider          │
│  - Generates final grounded response or streams SSE tokens  │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
                        Final Response
           (With tool metadata, intent, and provenance)
```

---

## Directory Structure

The AI Travel Agent is organized under `backend/app/ai/`:

```
backend/app/ai/
├── __init__.py                  # Root AI exports (TravelAgent, Orchestrator, etc.)
├── base.py                      # BaseAIProvider and AIResponse contracts
├── factory.py                   # Provider factory with dynamic provider resolution
├── agent/
│   ├── __init__.py              # Agent package exports
│   └── travel_agent.py          # TravelAgent class with run() and stream_run()
├── tools/
│   ├── __init__.py              # Tool registry & tool registrations
│   ├── base.py                  # BaseTool, ToolResult, DataProvenance
│   ├── registry.py              # ToolRegistry with execution metrics
│   ├── destination_tools.py     # search_destinations, search_attractions,
│   │                            # search_activities, search_local_database
│   ├── booking_tools.py         # search_hotels, search_restaurants,
│   │                            # search_flights, search_airports
│   ├── places_tools.py          # search_places, get_place_details
│   ├── geo_weather_tools.py     # get_weather, calculate_distance, calculate_route
│   └── trip_tools.py            # get_user_preferences, create_itinerary,
│                                # save_trip, retrieve_trip
├── prompts/
│   ├── __init__.py              # Prompts package exports
│   └── system_prompts.py        # Guardrail directives, intent prompts, templates
├── providers/
│   ├── __init__.py              # Provider exports
│   ├── gemini_provider.py       # Google Gemini REST provider
│   ├── openai_provider.py       # OpenAI GPT provider
│   └── local_provider.py        # Offline deterministic provider
└── orchestration/
    ├── __init__.py              # Orchestration package exports
    ├── intent_detector.py       # Semantic intent & entity classifier
    ├── tool_selector.py         # Tool parameter resolution & argument binding
    ├── context_builder.py       # Grounded context assembly & anti-fabrication prompt
    └── orchestrator.py          # TravelOrchestrator driving the complete lifecycle
```

---

## Catalog of 17 Travel Tools

| Tool Name | Scope | Primary Source | Fallback Source | Anti-Hallucination Guarantee |
|---|---|---|---|---|
| `search_destinations` | Curated destination discovery | Local Database | Knowledge Base | Returns curated DB facts, ratings, and ideal seasons. |
| `search_attractions` | Cultural sites, monuments, forts | Local Database | Regional POIs | Never fabricates ticket prices or opening hours. |
| `search_activities` | Experiences, treks, workshops | Amadeus Experiences | Local DB | Live supplier if configured; otherwise tagged as reference. |
| `search_hotels` | Accommodations & homestays | Amadeus Hotels | Local DB | Explicit warning attached if live inventory is unverified. |
| `search_restaurants` | Regional cuisines, local dining | Local Database | Curated Cafes | Live table availability is explicitly marked unverified. |
| `search_flights` | Flight routes & schedule offers | Amadeus Flight Offers | Regional GDS Cache | Live fare tag only if supplier responded; otherwise estimate. |
| `search_airports` | IATA airport lookup & hubs | Amadeus / Local DB | Geocoded hubs | Factual IATA resolution (DEL, BOM, CCU, JAI, etc.). |
| `search_places` | Points of interest & landmarks | Google Places (New) | Local POIs | Grounded POI data via field-masked Places API. |
| `get_place_details` | In-depth address, phone, hours | Google Places (New) | Local POIs | Displays operating hours notice to verify locally. |
| `get_weather` | Climate & packing guidance | Seasonal Climatology | Regional Index | Historical regional averages; advises checking daily radar. |
| `calculate_distance` | Haversine + road multiplier | Calculated | Road Benchmark | Distinguishes straight-line vs actual road distance & drive time. |
| `calculate_route` | Multi-stop waypoint sequencing | Calculated | Multi-leg route | Estimates realistic highway transit times across India. |
| `search_local_database` | Cross-table full-text search | PostgreSQL / SQLite | - | Strict DB-only verified records. |
| `get_user_preferences` | Traveler style, pace, budget | User Session / Profile | Default Persona | Loads authentic slow-travel preferences from DB. |
| `create_itinerary` | Multi-day sequenced itinerary | Generator Engine | Curated Template | Structured day-by-day morning/afternoon/evening slots. |
| `save_trip` | Persists itinerary to database | Local Database | - | Generates UUID + URL-safe `share_token`. |
| `retrieve_trip` | Fetches saved trip by ID/token | Local Database | - | Loads complete day sequence from database. |

---

## Intent Detection & Tool Selection Mapping

The `IntentDetector` categorizes incoming traveler queries and binds the exact tools required:

| User Query Example | Detected Intent | Required Tools Selected |
|---|---|---|
| *"Best places to visit in India?"* | `DESTINATION_DISCOVERY` | `search_destinations` |
| *"Find hotels in Jaipur."* | `HOTEL_SEARCH` | `search_hotels`, `search_places` |
| *"Plan a 5-day Rajasthan trip."* | `ITINERARY_PLANNING` | `search_destinations`, `search_attractions`, `search_activities`, `search_hotels`, `calculate_distance`, `create_itinerary` |
| *"Find me flights from Kolkata to Delhi."* | `FLIGHT_SEARCH` | `search_flights` |
| *"What is the weather like in Manali in October?"* | `WEATHER_INQUIRY` | `get_weather` |
| *"How far is Jaipur from Jodhpur?"* | `ROUTE_CALCULATION` | `calculate_distance` |
| *"Tell me about Hawa Mahal details."* | `PLACE_INQUIRY` | `get_place_details`, `search_places` |
| *"Save this 5-day itinerary."* | `TRIP_MANAGEMENT` | `save_trip` |
| *"Load my saved trip trip-abc1234."* | `TRIP_MANAGEMENT` | `retrieve_trip` |

---

## Provenance & Anti-Hallucination Guardrails

Every `ToolResult` generated by a travel tool carries a `DataProvenance` enum:

- `LIVE_API`: Direct live supplier response (e.g., Amadeus API, Google Places API).
- `LOCAL_DATABASE`: Verified record from local PostgreSQL/SQLite database.
- `ESTIMATE_RECOMMENDATION`: Curated baseline, historical climatology, or indicative benchmark.
- `CALCULATED`: Geodesic/mathematical derivation (e.g. Haversine distance, highway multiplier).
- `SYSTEM_STATE`: Application database state (e.g., saved itinerary, user preferences).

### Enforcement Rule:
When `is_live_data` is `False` and provenance is `LOCAL_DATABASE` or `ESTIMATE_RECOMMENDATION`:
1. The tool result automatically attaches an explicit warning string.
2. The `ContextBuilder` appends a critical guardrail directive instructing the LLM:
   > *"Some or all tool data originated from local directory cache or historical regional benchmarks. You MUST state clearly that pricing and availability are indicative estimates or seasonal reference values, NOT live verified supplier confirmations."*
3. The LLM response communicates this clearly to the user, ensuring full transparency.

---

## Integration with Chat Service & REST API

The `TravelAgent` is integrated into the core `ChatService` (`backend/app/services/chat_service.py`):
- **Synchronous Messages (`POST /api/v1/chat/conversations/{id}/messages`)**: Automatically executes the orchestration pipeline, attaches tool usage metadata to the message record in database (`metadata_json["tools_used"]`, `metadata_json["intent"]`, `metadata_json["is_live"]`), and returns the grounded answer.
- **Server-Sent Events (`POST /api/v1/chat/conversations/{id}/messages?stream=true`)**: Emits an initial `event: agent_activity` indicating detected intent and tools executed, followed by continuous token streaming (`event: token`), and finishes with `event: done`.

---

## Standalone Python Usage

```python
from backend.app.ai.agent.travel_agent import travel_agent

# Run full tool-using agent
response = await travel_agent.run(
    user_message="Plan a 5-day Rajasthan trip for heritage homestays.",
)

print("Intent:", response.intent)
print("Tools Used:", response.tools_used)
print("Is Live Data:", response.is_live)
print("Content:\n", response.content)
```
