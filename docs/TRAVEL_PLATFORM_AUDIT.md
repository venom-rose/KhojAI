# KHOJAI Travel Platform Audit & Integration Architecture

**Document Version:** 1.0.0  
**Target Milestone:** Transformation from Generic AI to Full AI Travel Intelligence Platform  
**Status:** Architectural Audit & Design Phase (No Code Modifications Executed)

---

## Part 1: Comprehensive Current State Audit

### 1. Existing Backend Architecture
The backend is built as an asynchronous service-oriented application using **Python 3.11/3.14**, **FastAPI 0.115+**, **Uvicorn**, and **SQLAlchemy 2.0 (Async)**:
* **Application Factory (`main.py`):** Configures application lifespan, structured request logging middleware (`log_requests`), HTTP defensive headers middleware (`add_security_headers`), CORS middleware (`CORSMiddleware`), and global exception handlers.
* **API Router (`backend/app/api/v1/router.py`):** Central router mounting modular sub-routers (`/auth`, `/users`, `/chat`, `/documents`, `/search`) and the diagnostic health probe (`GET /api/v1/health`).
* **Dependency Injection (`backend/app/api/deps.py`):** Provides scoped database sessions (`get_db`), bearer/cookie token resolution (`get_token_from_request`), strict user authentication (`get_current_user`), optional guest authentication (`get_optional_current_user`), and role-based access control (`require_role`).
* **Configuration Subsystem (`backend/app/config/settings.py`):** Pydantic `BaseSettings` reading from `.env`, enforcing cryptographically secure secrets (minimum 32-character JWT secrets), configuring storage directories (`MEDIA_DIR`), and selecting AI providers (`AI_PROVIDER`).
* **Structured Logging & Diagnostics:** Request timing in milliseconds, client IP logging, and live database connection probing (`SELECT 1`).

---

### 2. Existing Database Models
All entities inherit from `Base` with reusable mixins (`UUIDPrimaryKeyMixin`, `TimestampMixin`, `SoftDeleteMixin`) in `backend/app/models/`:

| Model | Table Name | Purpose & Key Columns | Relationships |
| :--- | :--- | :--- | :--- |
| **`User`** | `users` | User identity, email, bcrypt `hashed_password`, role, `is_active`, `is_verified`, `theme_preference`, `travel_preferences` (JSONB). | `sessions`, `conversations`, `documents`, `itineraries`, `contributions` |
| **`Session`** | `sessions` | Refresh/session token tracking, `session_token` (64-char hex), IP, user agent, expiration, revocation. | `user` |
| **`Destination`** | `destinations` | Primary destination record: `slug`, `name`, `state`, `region`, `category`, `best_season`, `budget`, `trust_score`, `description`, `image_url`, `coordinate_x`, `coordinate_y`, `is_published`. | `trust_metric`, `tags`, `stories`, `contributions`, `itineraries` |
| **`DestinationTag`** | `destination_tags` | Normalized tag keywords (`Slow travel`, `Rice terraces`, `Monasteries`). | `destination` |
| **`TrustMetric`** | `trust_metrics` | Destination Intelligence metrics: `source_quality`, `recency`, `community_agreement`, `completeness` (all 0-100), `last_audited_at`. | `destination` (1:1) |
| **`Itinerary`** | `itineraries` | Travel itinerary schema: `share_token`, `title`, `subtitle`, `summary`, `total_budget`, `preferences` (JSON), `match_score`, `rationale_bullets` (JSON list). | `user`, `primary_destination`, `days` |
| **`ItineraryDay`** | `itinerary_days` | Sequenced daily plan: `day_number`, `place_name`, `title`, `body`, `accent_color`, `sort_order`. | `itinerary` (cascade) |
| **`Contribution`** | `contributions` | Crowdsourced travel notes: `place_name`, `author_name`, `content`, `category`, `status`, `upvotes`. | `destination`, `user` |
| **`CommunityStory`** | `community_stories` | Highlighted traveler perspectives: `author_name`, `author_role`, `quote`, `tag`, `author_initials`. | `destination` |
| **`Document`** | `documents` | Ingested guidebooks & field notes: `storage_path`, `file_size_bytes`, `mime_type`, `status`, `chunk_count`. | `user`, `chunks` (cascade) |
| **`DocumentChunk`** | `document_chunks` | Text fragments for RAG: `chunk_index`, `chunk_content`, `token_count`, `embedding_json`, `metadata_json`. | `document` (cascade) |
| **`Conversation`** | `conversations` | AI chat session: `title`, `model`, `is_pinned`, `is_archived`. | `user`, `messages` (cascade) |
| **`ChatMessage`** | `chat_messages` | Chat entries: `sender_type` (`user`/`assistant`/`system`), `content`, `model_name`, `token_count`. | `conversation` (cascade) |

---

### 3. Existing AI Provider Implementation
Located in `backend/app/ai/`:
* **Abstract Base Interface (`base.py`):** Defines `BaseAIProvider` with async methods `generate_response()` and `stream_response()`.
* **Provider Implementations:**
  * `LocalAIProvider`: Offline fallback producing contextual responses for travel queries and RAG questions without external API tokens.
  * `GeminiProvider`: Google Gemini 1.5 Flash via REST endpoints with `x-goog-api-key` header and Server-Sent Events (SSE) streaming.
  * `OpenAIProvider`: OpenAI GPT-4o-mini via REST endpoints with bearer authorization.
* **Factory Pattern (`get_ai_provider()`):** Dynamically instantiates the configured provider based on `settings.AI_PROVIDER` (`local`, `gemini`, or `openai`).

---

### 4. Existing RAG Implementation
Located in `backend/app/rag/` and `backend/app/services/document_service.py`:
* **File Ingestion:** Secure upload handling validating extension, MIME type, 20MB file size limit, and preventing path traversal via UUID filenames (`doc_{uuid}.dat`).
* **Text Cleaner (`cleaner.py`):** Strips null bytes, normalizes carriage returns, and sanitizes formatting.
* **Chunker Engine (`chunker.py`):** Sliding-window chunking (default 500 words, 100 overlap) respecting paragraph boundaries.
* **Embeddings & Similarity (`embeddings.py`):** Normalizes text into 384-dimensional vectors with cosine similarity calculation.
* **Prompt Injection Defenses:** Encapsulates context in `<travel_knowledge_context>` tags and sanitizes closing tags to prevent context breakout.

---

### 5. Existing Search Implementation
Located in `backend/app/services/search_service.py`:
* **Global Omnisearch (`GET /api/v1/search`):** Multi-collection search combining destinations, private user documents, and conversation history.
* **Destination Faceted Search (`GET /api/v1/search/destinations`):** Full-text SQL filtering matching the Discover page filters (region, state, budget, travel style, seasonality, experience, and sorting).
* **Document Hybrid Search (`GET /api/v1/search/documents`):** Combines keyword filtering with vector cosine similarity.
* **User Isolation:** All search routines enforce tenancy scoping, preventing users from seeing other users' private documents or chats.

---

### 6. Existing API Endpoints

| Category | Method | Path | Status |
| :--- | :--- | :--- | :---: |
| **System** | `GET` | `/api/v1/health` | Implemented (Active Diagnostics) |
| **Auth** | `POST` | `/api/v1/auth/register` | Implemented |
| **Auth** | `POST` | `/api/v1/auth/login` | Implemented |
| **Auth** | `POST` | `/api/v1/auth/refresh` | Implemented |
| **Auth** | `POST` | `/api/v1/auth/logout` | Implemented |
| **Auth** | `GET` | `/api/v1/auth/me` | Implemented |
| **Users** | `GET` | `/api/v1/users/me` | Implemented |
| **Users** | `PATCH` | `/api/v1/users/me` | Implemented |
| **Users** | `PATCH` | `/api/v1/users/me/preferences` | Implemented |
| **Users** | `DELETE`| `/api/v1/users/me` | Implemented |
| **Chat** | `POST` | `/api/v1/chat/conversations` | Implemented |
| **Chat** | `GET` | `/api/v1/chat/conversations` | Implemented |
| **Chat** | `GET` | `/api/v1/chat/conversations/{id}` | Implemented |
| **Chat** | `PATCH` | `/api/v1/chat/conversations/{id}` | Implemented |
| **Chat** | `DELETE`| `/api/v1/chat/conversations/{id}` | Implemented |
| **Chat** | `GET` | `/api/v1/chat/conversations/{id}/messages` | Implemented |
| **Chat** | `POST` | `/api/v1/chat/conversations/{id}/messages` | Implemented (SSE streaming supported) |
| **Chat** | `POST` | `/api/v1/chat/conversations/{id}/messages/{msg_id}/regenerate` | Implemented |
| **Docs** | `POST` | `/api/v1/documents` | Implemented |
| **Docs** | `GET` | `/api/v1/documents` | Implemented |
| **Docs** | `GET` | `/api/v1/documents/{id}` | Implemented |
| **Docs** | `POST` | `/api/v1/documents/{id}/reprocess` | Implemented |
| **Docs** | `DELETE`| `/api/v1/documents/{id}` | Implemented |
| **Docs** | `POST` | `/api/v1/documents/query` | Implemented (RAG Q&A) |
| **Docs** | `POST` | `/api/v1/documents/search` | Implemented |
| **Search** | `GET` | `/api/v1/search` | Implemented (Omnisearch) |
| **Search** | `GET` | `/api/v1/search/destinations` | Implemented |
| **Search** | `GET` | `/api/v1/search/documents` | Implemented |
| **Search** | `GET` | `/api/v1/search/conversations` | Implemented |

---

### 7. Existing Frontend Travel-Related Components
Located in `client/src/`:
1. **`Discover.tsx`:** Destination exploration view with reactive search query, region selector, state dropdown, budget options, travel style tags, best season selectors, and sorting dropdown.
2. **`DestinationDetail.tsx`:** Single destination presentation displaying hero imagery, TrustScore radar breakdown, key context cards (Best season, Estimated cost, Accessibility, Local experiences, How to reach, Stay options), and community voices.
3. **`Planner.tsx`:** 5-step interactive briefing wizard (Budget, Duration, Style, Interests, Group) with multi-step animated progress bars.
4. **`PlannerResults.tsx`:** Shortlist presentation with match scores, explainability metrics, side-by-side comparison tray, and a generated day-by-day itinerary route.
5. **`Contribute.tsx`:** Crowdsourced field notes submission form with file upload integrated into the RAG document service.
6. **`Community.tsx`:** Traveler community stories and local perspectives.
7. **`ChatModal.tsx`:** Floating AI travel copilot drawer supporting multi-turn conversation and real-time streaming.
8. **`GlobalSearchDialog.tsx`:** Universal `⌘K` omnisearch dialog.
9. **`DocumentModal.tsx`:** Knowledge vault upload manager.

---

### 8. Existing Mock Travel Data
Located in `client/src/data/destinations.ts`:
* **Static Destinations (8 records):**
  1. `ziro` (Arunachal Pradesh, Northeast) — Slow travel, Rice terraces, Local food
  2. `majuli` (Assam, Northeast) — Island life, Satras, Cycling
  3. `tirthan-valley` (Himachal Pradesh, Himalayas) — River walks, Cedar forest, Cabin stays
  4. `gandikota` (Andhra Pradesh, South) — Red gorge, Sunrise, Road trip
  5. `chopta` (Uttarakhand, Himalayas) — Alpine trails, Birding, Sunrise
  6. `orchha` (Madhya Pradesh, Central India) — Riverside ruins, Craft, Architecture
  7. `dzukou-valley` (Nagaland, Northeast) — High valley, Seasonal bloom, Trekking
  8. `gurez-valley` (Jammu & Kashmir, Himalayas) — Wooden homes, High valley, Community stays
* **Static Itinerary (`demoItinerary`):** 5-day Northeast loop ("A slower side of the Northeast: Ziro → Majuli").
* **Static Recommendation Logic (`buildPlannerRecommendations`):** Client-side heuristic matching preference keywords against static destination tags.
* **Static Map Mock (`MapMock`):** SVG visualization with hardcoded coordinate pins (`71%, 24%`, etc.).

---

### 9. Existing Travel-Related UI Fields
* **Destination Entity:**
  `slug`, `name`, `state`, `region`, `category`, `tags[]`, `bestSeason`, `budget` (`₹`, `₹₹`, `₹₹₹`), `trustScore` (0–100), `description`, `image`, `accent`, `coordinates` (`{ x, y }`), `trustMetrics` (`sourceQuality`, `recency`, `communityAgreement`, `completeness`), `demoNote`.
* **Planner Inputs:**
  * `budget`: `₹8,000`, `₹15,000`, `₹25,000`, `Keep it open`
  * `days`: `3 days`, `5 days`, `7 days`, `10+ days`
  * `style`: `Slow travel`, `Outdoors`, `Culture-led`, `Road trip`
  * `interests`: `Nature`, `Culture`, `Food`, `Outdoors`, `Heritage`, `Slow travel`
  * `group`: `Just me`, `2 people`, `3–5 people`, `A small group`
* **Itinerary Presentation:**
  `title`, `subtitle`, `summary`, `totalBudget`, `matchScore`, `reasons[]`, `days[]` (`day`, `place`, `title`, `body`, `accent`).
* **Context Cards in Destination Detail:**
  `Best season`, `Estimated cost`, `Accessibility`, `Local experiences`, `How to reach`, `Stay options`.

---

### 10. Missing Functionality Required for a Real AI Travel Assistant
1. **Backend Itinerary Generation API:** Currently, `PlannerResults.tsx` calls client-side mock functions. There is no `POST /api/v1/itineraries/generate` endpoint or backend database persistence for generated plans.
2. **Structured Attraction Records:** Attractions are currently summarized in plain text strings inside destination descriptions rather than structured, queryable entities with operating hours, ticket fees, and guidelines.
3. **Structured Stays & Community Homestays:** Stays are currently represented by a single text line in `DestinationDetail.tsx` ("Community stay, small guesthouse or homestay — availability is not live").
4. **Structured Eateries & Culinary Guides:** No dedicated model for regional food, local dhabas, tea houses, or traditional kitchens.
5. **Structured Activities & Experiences:** No structured catalog of local experiences (e.g. Apatani agricultural tours, Majuli mask-making workshops, high-altitude alpine treks).
6. **Transit & Transportation Hubs:** No structured representation of gateway airports, railheads, bus routes, or ferry ghats.
7. **Weather & Seasonality Intelligence:** No live weather forecasts, seasonal temperature ranges, monsoon alerts, or high-altitude advisory feeds.
8. **Point-to-Point Distances & Travel Times:** No distance matrix calculation between major transit hubs (Guwahati, Dibrugarh, Chandigarh, Dehradun) and offbeat destinations.
9. **AI Travel Assistant Agentic Tools:** The AI Copilot operates purely on conversation and document RAG. It lacks function-calling tools to query the destination catalog, inspect verified stays, or compile a customized day-by-day itinerary directly from chat.

---

## Part 2: Integration Architecture Design

To transform KHOJAI into a comprehensive travel intelligence platform **without replacing or breaking any existing component**, the architecture will be extended as follows:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EXTENDED DATA MODEL                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                            ┌───────────────────┐                            │
│                            │    Destination    │                            │
│                            │   (Core Anchor)   │                            │
│                            └─────────┬─────────┘                            │
│                                      │                                      │
│       ┌──────────────┬───────────────┼───────────────┬──────────────┐       │
│       ▼              ▼               ▼               ▼              ▼       │
│ ┌────────────┐ ┌────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────┐ │
│ │ Attraction │ │    Stay    │ │   Eatery    │ │  Activity  │ │ TransitHub │ │
│ │ (Points of │ │ (Homestays │ │ (Indigenous │ │ (Workshops │ │ (Airports, │ │
│ │  Interest) │ │  & Lodges) │ │  & Dhabas)  │ │  & Treks)  │ │  Railheads)│ │
│ └────────────┘ └────────────┘ └─────────────┘ └────────────┘ └────────────┘ │
│                                      │                                      │
│                                      ▼                                      │
│                            ┌───────────────────┐                            │
│                            │   RouteSegment    │                            │
│                            │(Distance, Timing, │                            │
│                            │ Road Conditions)  │                            │
│                            └───────────────────┘                            │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                         TRAVEL INTELLIGENCE SERVICES                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  • WeatherService: Seasonal forecasts, temperature ranges & monsoon alerts │
│  • RoutingService: Point-to-point transit calculations & mountain passes    │
│  • ItineraryService: AI-driven day-by-day sequencing & budget breakdown     │
│  • TravelAssistantService: Agentic LLM tool execution & structured planning│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 1. Destination Database Extension
Extend the existing `Destination` model and table with spatial and practical logistics:
* `latitude`: Float (e.g. `27.5956`)
* `longitude`: Float (e.g. `93.8385`)
* `elevation_meters`: Integer (e.g. `1572` m for Ziro, `3800` m for Spiti)
* `nearest_airport`: String (e.g. `Hollongi Airport, Itanagar (120 km)`)
* `nearest_railhead`: String (e.g. `Naharlagun Railway Station (100 km)`)
* `permit_requirements`: String (e.g. `Inner Line Permit (ILP) required for non-Arunachal residents`)
* `cultural_etiquette`: Text (e.g. `Ask elders before photographing face tattoos; remove shoes before entering traditional Apatani bamboo homes`)
* `connectivity_rating`: String (`Moderate 4G in town center, intermittent on high trails`)

---

### 2. Attractions Entity (`attractions`)
Structured points of interest within or surrounding a destination:
* `id`: UUID (Primary Key)
* `destination_id`: UUID (Foreign Key → `destinations.id`, ondelete `CASCADE`)
* `name`: String (e.g. `Hong Village Bamboo Groves`, `Kile Pakho Viewpoint`)
* `category`: String (`Village`, `Monastery`, `Viewpoint`, `Waterfall`, `Sacred Grove`, `Craft Center`)
* `description`: Text
* `entry_fee`: String (`Free`, `₹50 per person`)
* `timings`: String (`Sunrise to Sunset`, `09:00 - 17:00`)
* `physical_difficulty`: String (`Easy`, `Moderate`, `Strenuous`)
* `best_time_of_day`: String (`Early morning`, `Golden hour`)
* `latitude`, `longitude`: Optional Floats

---

### 3. Hotels & Homestays Entity (`stays`)
Authentic accommodation directory prioritizing rural homestays and community lodges:
* `id`: UUID (Primary Key)
* `destination_id`: UUID (Foreign Key → `destinations.id`, ondelete `CASCADE`)
* `name`: String (e.g. `Apatani Cultural Homestay`, `Donyi Hango Homestay`)
* `stay_type`: String (`community_homestay`, `eco_lodge`, `cabin`, `monastery_guesthouse`, `campsite`)
* `price_per_night`: String (e.g. `₹1,200 – ₹2,000 / night including home-cooked meals`)
* `host_name`: String (e.g. `Tage Kanya & Family`)
* `amenities`: JSON List (e.g. `["Hot water by fire", "Organic home garden", "Local guide on request", "Traditional hearth"]`)
* `sustainability_score`: Integer (1–100)
* `contact_info`: String (e.g. `Phone / WhatsApp / Village council contact`)
* `image_url`: String

---

### 4. Restaurants & Eateries Entity (`eateries`)
Indigenous food culture, tea houses, and local kitchens:
* `id`: UUID (Primary Key)
* `destination_id`: UUID (Foreign Key → `destinations.id`, ondelete `CASCADE`)
* `name`: String (e.g. `Apatani Kitchen`, `Majuli Organic Rice House`)
* `cuisine_type`: String (`Indigenous Tribal`, `Assamese Thali`, `Tibetan / Himalayan`, `Pure Vegetarian`)
* `must_try_dishes`: JSON List (e.g. `["Piku (bamboo shoot pork/veg)", "Apong (rice brew)", "Millet flatbread"]`)
* `average_cost_per_meal`: String (e.g. `₹150 – ₹300`)
* `hygiene_notes`: String (e.g. `Boiled mountain spring water, fresh hearth cooking`)

---

### 5. Activities & Cultural Experiences Entity (`activities`)
Immersive experiences led by local residents:
* `id`: UUID (Primary Key)
* `destination_id`: UUID (Foreign Key → `destinations.id`, ondelete `CASCADE`)
* `title`: String (e.g. `Paddy-cum-Fish Cultivation Walk`, `Traditional Mask Making Workshop`)
* `activity_type`: String (`Cultural Walk`, `Craft Workshop`, `Day Trek`, `Birdwatching`, `Culinary Masterclass`)
* `duration_hours`: Float (e.g. `3.5`)
* `seasonality`: String (e.g. `July – October during paddy planting and harvest`)
* `guide_required`: Boolean (`True`)
* `estimated_cost`: String (e.g. `₹500 – ₹800 community guide honorarium`)
* `description`: Text

---

### 6. Transit Hubs Entity (`transit_hubs`)
Gateway connectivity points linking major transit arteries to rural locations:
* `id`: UUID (Primary Key)
* `destination_id`: UUID (Foreign Key → `destinations.id`, ondelete `CASCADE`)
* `hub_type`: String (`airport`, `railway_station`, `bus_stand`, `ferry_ghat`)
* `name`: String (e.g. `Naharlagun Railway Station`, `Jorhat Nimati Ghat Ferry`)
* `code`: Optional String (`NHLN`, `GAU`, `IXS`)
* `distance_km`: Float (e.g. `98.5`)
* `transfer_time_hours`: Float (e.g. `3.5`)
* `transfer_modes`: JSON List (e.g. `["Shared Sumo taxi (₹350)", "Private cab (₹3,000)", "State transport bus"]`)

---

### 7. Transportation & Route Segments (`route_segments`)
Inter-destination and transit corridor routing details:
* `id`: UUID (Primary Key)
* `origin_name`: String (e.g. `Guwahati`, `Naharlagun`, `Jorhat`)
* `destination_id`: UUID (Foreign Key → `destinations.id`, ondelete `CASCADE`)
* `distance_km`: Float
* `duration_hours`: Float
* `road_condition`: String (`Smooth metalled highway`, `Mountain winding road`, `Seasonal gravel trail`)
* `transit_mode`: String (`Drive / Cab`, `Train + Taxi`, `River Ferry`, `Trek on foot`)
* `travel_tips`: Text (e.g. `Start before 7:00 AM to avoid mountain mist; keep cash for toll checkpoints`)

---

### 8. Weather & Climate Intelligence Service (`WeatherService`)
A dedicated service providing historical and seasonal meteorological intelligence:
* **Seasonal Temperature Profiles:** Monthly daytime and nighttime temperature ranges.
* **Monsoon & Rainfall Risk Indicators:** Alerts for high-rainfall periods (June–September in Northeast/Western Ghats).
* **Altitude & Cold Weather Advisories:** Wind chill and snow advisories for Himalayan destinations above 2,500m.
* **Best Window Recommendation:** Correlates traveler style with optimal climate conditions.

---

### 9. Travel Distances & Routing Engine (`RoutingService`)
Computes realistic journey metrics:
* Calculates driving and transit travel times with realistic mountain/rural speed multipliers ($25\text{–}35\text{ km/h}$ in hill terrain vs $60\text{–}70\text{ km/h}$ on plains).
* Mountain pass status intelligence (e.g. Kunzum La status May–October vs winter closure).
* Transit buffer recommendation: Suggests required layover buffers for unpredictable rural transfers.

---

### 10. User Personalization Engine
Deepens the existing `travel_preferences` JSON in the `User` model:
* Travel pacing (`unhurried`, `balanced`, `active`)
* Preferred stay style (`homestay_only`, `eco_lodge`, `budget_friendly`, `comfortable`)
* Dietary preferences (`strictly_vegetarian`, `local_traditional`, `jain`, `no_preference`)
* Fitness level (`light_walking`, `moderate_hiker`, `experienced_trekker`)
* Cultural interests (`indigenous_crafts`, `wildlife_birding`, `sacred_architecture`, `culinary_heritage`)

---

### 11. AI Trip Planning & Itinerary Generation Engine (`ItineraryService`)
Upgrades the current mock `buildPlannerRecommendations` and `demoItinerary` into a real backend AI pipeline:
* **Endpoint:** `POST /api/v1/itineraries/generate`
  * **Payload:** `PlannerPreferencesIn` (budget, days, style, interests, group, starting_city).
  * **Workflow:**
    1. Query destination database matching region, budget, style, and season.
    2. Rank top 3 destination matches with explainability scores (Budget fit, Style fit, Experience fit, Season fit).
    3. Invoke AI Provider with structured travel schema to synthesize day-by-day itinerary:
       - Morning, afternoon, and evening recommendations.
       - Real stays and homestays chosen from the `stays` table.
       - Real activities chosen from the `activities` table.
       - Authentic local food spots chosen from `eateries`.
       - Transit logistics between days.
    4. Persist result in `itineraries` and `itinerary_days` database tables.
    5. Return unique `share_token` for public sharing.
* **Endpoint:** `GET /api/v1/itineraries/{share_token}`
  * Retrieves saved itinerary from database with all day stops, stays, and budget estimates.

---

### 12. AI Travel Assistant Integration (Agentic Copilot)
Upgrades the `ChatModal` from a generic conversational bot into a travel agent equipped with tool-calling capabilities:
* **Tool: `search_destinations(filters)`:** Queries verified destinations from PostgreSQL.
* **Tool: `get_destination_intel(slug)`:** Retrieves trust scores, cultural etiquette, permits, and attractions.
* **Tool: `get_stays_and_homestays(destination_slug)`:** Fetches verified homestays with hosts and pricing.
* **Tool: `calculate_route(origin, destination)`:** Returns distance, transit options, and travel times.
* **Tool: `build_itinerary(brief)`:** Compiles and saves an actionable day-by-day plan.
* **Tool: `query_knowledge_vault(question)`:** Performs RAG retrieval over uploaded field notes.

---

### 13. API Contracts for New Travel Endpoints

```text
# Destinations & Discovery
GET    /api/v1/destinations                     # List all published destinations
GET    /api/v1/destinations/{slug}              # Full destination intelligence record
GET    /api/v1/destinations/{slug}/attractions  # Points of interest and sacred sites
GET    /api/v1/destinations/{slug}/stays        # Verified homestays and eco-lodges
GET    /api/v1/destinations/{slug}/eateries     # Local food culture and kitchens
GET    /api/v1/destinations/{slug}/activities   # Experiences and cultural workshops
GET    /api/v1/destinations/{slug}/transit      # Gateway airports, railheads, and roads
GET    /api/v1/destinations/{slug}/weather      # Seasonal climate profile and alerts

# Trip Planning & Itineraries
POST   /api/v1/itineraries/generate             # Generate AI trip recommendations & route
GET    /api/v1/itineraries/{share_token}        # Retrieve persisted itinerary by share token
POST   /api/v1/itineraries/{id}/save            # Save/bookmark itinerary to user profile
GET    /api/v1/users/me/itineraries             # List authenticated user's saved itineraries

# Routing & Transit
GET    /api/v1/routing/calculate                # Route distance, duration, and conditions
```

---

### 14. Non-Destructive Frontend Integration Strategy
* **Preserve All Existing UI Styles & Typography:** The earthy editorial theme, Radix components, and Framer Motion transitions remain untouched.
* **Gradual Service Connection:**
  * Connect `client/src/pages/Discover.tsx` to `GET /api/v1/destinations`.
  * Connect `client/src/pages/DestinationDetail.tsx` to `GET /api/v1/destinations/{slug}` with real stays, attractions, and how-to-reach data replacing static text.
  * Connect `client/src/pages/Planner.tsx` and `PlannerResults.tsx` to `POST /api/v1/itineraries/generate` and `GET /api/v1/itineraries/{share_token}`, eliminating all `setTimeout` simulations.
  * Fallback to static cache in `client/src/data/destinations.ts` if offline, ensuring zero UI degradation.

---

## Part 3: Readiness & Next Steps

This audit establishes the blueprint for upgrading KHOJAI into a premier travel intelligence platform.  
**No code changes have been applied.** The system remains in a clean, passing state (81 automated tests passed).

Once approved, implementation can proceed in orderly phases:
1. **Phase 1: Database Migration & Entities** (Attractions, Stays, Eateries, Activities, TransitHubs, RouteSegments).
2. **Phase 2: Travel Intelligence Services** (WeatherService, RoutingService, ItineraryService).
3. **Phase 3: Backend REST Endpoints** (`/destinations/{slug}/*`, `/itineraries/generate`).
4. **Phase 4: Agentic Travel Assistant Tools** (Equipping AI Chat with database querying tools).
5. **Phase 5: Frontend Service Connection** (Connecting Discover, DestinationDetail, and Planner to live APIs).
