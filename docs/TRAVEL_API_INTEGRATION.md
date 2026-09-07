# KHOJAI Real Travel API Integration Architecture

## 1. Overview & Adapter Architecture

KHOJAI integrates live, enterprise-grade and free-tier travel APIs using a **pluggable adapter architecture**. This completely isolates business logic and user presentation from third-party vendor interfaces, preventing vendor lock-in and eliminating raw third-party schema leaks.

```
                               ┌───────────────────────────┐
                               │  FastAPI / Frontend Client│
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   TravelProviderService   │
                               │  (Cache, Circuit Breaker, │
                               │   Timeout & Failover)     │
                               └─────────────┬─────────────┘
                                             │
      ┌────────────────┬─────────────────────┼─────────────────────┬────────────────┬───────────────┐
      │                │                     │                     │                │               │
      ▼                ▼                     ▼                     ▼                ▼               ▼
┌───────────┐  ┌───────────────┐   ┌───────────────────┐   ┌───────────────┐ ┌─────────────┐ ┌─────────────┐
│  Amadeus  │  │ Google Places │   │   OpenTripMap     │   │   Geoapify    │ │  Nominatim  │ │  Local DB   │
│ (Flights, │  │ (Text Search, │   │ (POIs, Landmarks, │   │ (Categories,  │ │ (Geocoding, │ │ (Zero-Cost  │
│  Hotels,  │  │ Autocomplete, │   │ Cultural Objects, │   │ Proximity,    │ │ Rev-Geocode,│ │ PostgreSQL/ │
│Activities)│  │ Details,Photos│   │    Attractions)   │   │  Places V2)   │ │  OSM 1s cap)│ │   SQLite)   │
└─────┬─────┘  └───────┬───────┘   └─────────┬─────────┘   └───────┬───────┘ └──────┬──────┘ └──────┬──────┘
      │                │                     │                     │                │               │
      ▼                ▼                     ▼                     ▼                ▼               ▼
┌───────────┐  ┌───────────────┐   ┌───────────────────┐   ┌───────────────┐ ┌─────────────┐ ┌─────────────┐
│  Flight/  │  │     Place     │   │       Place/      │   │    Place/     │ │    Place    │ │ Destination/│
│   Hotel   │  │   Normalizer  │   │      Activity     │   │     Hotel     │ │ Normalizer  │ │     POI     │
│Normalizer │  │               │   │    Normalizer     │   │  Normalizer   │ │             │ │ Normalizer  │
└─────┬─────┘  └───────┬───────┘   └─────────┬─────────┘   └───────┬───────┘ └──────┬──────┘ └──────┬──────┘
      │                │                     │                     │                │               │
      └────────────────┴─────────────────────┼─────────────────────┴────────────────┴───────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │ Unified Internal Schemas: │
                               │ - TravelHotel             │
                               │ - TravelPlace             │
                               │ - TravelFlight            │
                               │ - TravelActivity          │
                               │ - TravelAirport           │
                               │ - TravelDestination       │
                               │ - TravelPhoto / Review    │
                               └───────────────────────────┘
```

---

## 2. Security & Credential Isolation

* **Backend Key Isolation**: All external API keys (`AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `GOOGLE_MAPS_API_KEY`, `OPENTRIPMAP_API_KEY`, `GEOAPIFY_API_KEY`) are stored **strictly on the backend** in environment variables.
* **No Frontend Exposure**: Provider keys are never transmitted to the frontend or exposed in HTTP responses.
* **Photo Proxying**: High-resolution place photos from Google Places and other providers are streamed through `/api/v1/travel/places/photos/{photo_name:path}`, protecting backend credentials and caching images securely.
* **Nominatim Fair Use**: Strict rate limiting (minimum 1.05-second spacing with `asyncio.Lock`) and an explicit `User-Agent` header (`NOMINATIM_USER_AGENT`) strictly abide by the OpenStreetMap Usage Policy.

### Environment Configuration

```env
# Amadeus Self-Service API
AMADEUS_CLIENT_ID=your_amadeus_api_key
AMADEUS_CLIENT_SECRET=your_amadeus_api_secret
AMADEUS_BASE_URL=https://test.api.amadeus.com   # Production: https://api.amadeus.com

# Google Maps / Places API (New)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
GOOGLE_PLACES_ENABLED=True

# OpenTripMap API
OPENTRIPMAP_API_KEY=your_opentripmap_api_key
OPENTRIPMAP_BASE_URL=https://api.opentripmap.com/0.1/en/places

# Geoapify API
GEOAPIFY_API_KEY=your_geoapify_api_key
GEOAPIFY_BASE_URL=https://api.geoapify.com

# Nominatim (OpenStreetMap)
NOMINATIM_BASE_URL=https://nominatim.openstreetmap.org
NOMINATIM_USER_AGENT=KHOJAI-Travel-App/1.0 (contact@khojai.com)

# Resilience & Provider Strategy
TRAVEL_PROVIDER_PRIMARY=amadeus
TRAVEL_PROVIDER_FALLBACK=local_db
TRAVEL_CACHE_TTL_SECONDS=3600
TRAVEL_API_TIMEOUT_SECONDS=10.0
TRAVEL_API_MAX_RETRIES=2
```

---

## 3. Provider Adapters & Responsibilities

| Provider Adapter | Module Path | Primary Capabilities | Fallback Hierarchy |
| :--- | :--- | :--- | :--- |
| **AmadeusProvider** | `backend.app.travel.providers.amadeus` | Flights, Hotel offers, Airport registries, Tours & Activities | AirLabs / Local DB |
| **GooglePlacesProvider** | `backend.app.travel.providers.google_places` | Text Search, Autocomplete, Place Details, Secure Photo Proxy | Geoapify / OpenTripMap / Local DB |
| **OpenTripMapProvider** | `backend.app.travel.providers.opentripmap` | Heritage, Natural Landmarks, Cultural Sites, Coordinates POI Discovery | Geoapify / Local DB |
| **GeoapifyProvider** | `backend.app.travel.providers.geoapify` | Category Place Search, Proximity Bias, Address Autocomplete | Nominatim / Local DB |
| **NominatimProvider** | `backend.app.travel.providers.nominatim` | Forward Geocoding, Reverse Geocoding (Coordinates to Place) | Local DB |
| **LocalDatabaseProvider** | `backend.app.travel.providers.local_database` | Ground-truth fallback for destinations, seeded POIs, hotels, airports | Final resilient fallback |

---

## 4. Provider-Independent Internal Schemas

All external responses are normalized into standard Pydantic models in `backend.app.travel.schemas.internal`:

### `TravelDestination`
```python
class TravelDestination(BaseModel):
    slug: str
    name: str
    state: Optional[str] = None
    country: Optional[str] = "India"
    country_code: Optional[str] = "IN"
    region: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    best_season: Optional[str] = None
    budget_tier: Optional[str] = None
    trust_score: Optional[int] = 85
    image_url: Optional[str] = None
    tags: List[str] = []
    provider: str = "local_db"
    provider_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
```

### `TravelHotel`
```python
class TravelHotel(BaseModel):
    name: str
    hotel_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    city_name: Optional[str] = None
    country_code: Optional[str] = "IN"
    rating: Optional[float] = None
    price_tier: Optional[str] = None
    price: Optional[float] = None
    currency: str = "INR"
    amenities: List[str] = []
    photo_urls: List[str] = []
    provider: str
    provider_id: Optional[str] = None
    booking_url: Optional[str] = None
```

### `TravelPlace`
```python
class TravelPlace(BaseModel):
    name: str
    place_id: Optional[str] = None
    formatted_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    types: List[str] = []
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    price_level: Optional[str] = None
    photos: List[TravelPhoto] = []
    reviews: List[TravelReview] = []
    phone_number: Optional[str] = None
    website_url: Optional[str] = None
    opening_hours: List[str] = []
    is_open_now: Optional[bool] = None
    provider: str
    provider_id: Optional[str] = None
```

### `TravelFlight` & `TravelActivity`
```python
class TravelFlight(BaseModel):
    offer_id: str
    airline_code: str
    airline_name: Optional[str] = None
    departure_airport: str
    arrival_airport: str
    departure_time: str
    arrival_time: str
    duration: str
    stops: int = 0
    price: float
    currency: str = "INR"
    segments: List[TravelFlightSegment] = []
    provider: str = "amadeus"

class TravelActivity(BaseModel):
    title: str
    description: Optional[str] = None
    activity_type: Optional[str] = None
    duration: Optional[str] = None
    price: Optional[float] = None
    currency: str = "INR"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    rating: Optional[float] = None
    pictures: List[str] = []
    provider: str
```

---

## 5. Domain Services Layer

The service layer in `backend.app.travel.services` encapsulates provider orchestration and intelligent caching:

1. **`TravelSearchService`**: Concurrent multi-domain search across destinations, places, hotels, and activities.
2. **`DestinationService`**: Curated destinations, slug lookup, and localized experiential tours.
3. **`HotelService`**: Multi-provider hotel lookup with Amadeus → Google Places → Geoapify → Local DB fallback.
4. **`FlightService`**: Flight offers and airport lookup via Amadeus → AirLabs → Local DB.
5. **`ActivityService`**: Experiential travel and POI discovery via Amadeus → OpenTripMap → Geoapify → Local DB.
6. **`PlaceService`**: Points of interest, predictive autocomplete, place details, and photo streaming via Google Places → Geoapify → OpenTripMap → Nominatim → Local DB.
7. **`TravelProviderService`**: High-level provider health checks and circuit breaker coordination.

---

## 6. Endpoints Reference

### Root Health & Status
* `GET /api/travel/providers`: Safe status of configured providers without exposing API credentials.
* `GET /api/health/travel`: Readiness and health probe of the travel data layer and active cache.

### Travel Domain API (`/api/v1/travel`)
* `GET /api/v1/travel/search?query=Goa`: Concurrent multi-domain travel search.
* `GET /api/v1/travel/destinations/search?query=Ziro`: Filter destinations by query, state, or category.
* `GET /api/v1/travel/destinations/{slug}`: Detailed destination profile.
* `GET /api/v1/travel/destinations/{slug}/experiences`: Destination activities and tours.
* `GET /api/v1/travel/places/nearby?latitude=27.59&longitude=93.83&radius_meters=5000`: Coordinates-based POI search.
* `GET /api/v1/travel/places/search?query=Monastery`: Text query place search.
* `GET /api/v1/travel/places/details?place_id=...`: Full place profile and reviews.
* `GET /api/v1/travel/places/autocomplete?input_text=Tawang`: Keystroke predictive search.
* `GET /api/v1/travel/places/photos/{photo_name}`: Proxied binary photo stream.
* `GET /api/v1/travel/hotels/search?city_code=DEL`: Hotel search by city or coordinates.
* `GET /api/v1/travel/flights/search?origin=DEL&destination=GAU&departure_date=2026-10-15`: Flight offer search.
* `GET /api/v1/travel/activities/search?latitude=27.59&longitude=93.83`: Activity and tour search.
* `GET /api/v1/travel/airports/search?keyword=HGI`: Airport and transit hub discovery.
