# KHOJAI Real Travel API Integration Architecture

## 1. Overview & Adapter Architecture

KHOJAI integrates live, enterprise-grade travel APIs using an **adapter architecture**. This decouples application business logic and UI presentation from specific external vendors. Providers can be added, updated, or replaced without changing internal application schemas or breaking frontend contracts.

```
                               ┌───────────────────────────┐
                               │  FastAPI / Frontend Client│
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   TravelProviderService   │
                               │(Cache, Timeout, Resilience│
                               │   & Local DB Fallback)    │
                               └─────────────┬─────────────┘
                                             │
                       ┌─────────────────────┼─────────────────────┐
                       │                     │                     │
                       ▼                     ▼                     ▼
             ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
             │  AmadeusProvider  │ │GooglePlacesProvider│ │LocalDatabaseProv. │
             │  (Hotels, Flights,│ │ (Search, Details, │ │ (Verified Offbeat │
             │Airports,Activities│ │Autocomplete,Photos│ │   PostgreSQL/DB)  │
             └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
                       │                     │                     │
                       ▼                     ▼                     ▼
             ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
             │ AmadeusNormalizer │ │ GoogleNormalizer  │ │  LocalNormalizer  │
             └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
                       │                     │                     │
                       └─────────────────────┼─────────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │ Provider-Independent      │
                               │ Internal Schemas:         │
                               │ - TravelHotel             │
                               │ - TravelPlace             │
                               │ - TravelFlight            │
                               │ - TravelActivity          │
                               │ - TravelAirport           │
                               └───────────────────────────┘
```

---

## 2. Security & Credential Isolation

* **Strict Backend Isolation**: External provider API keys (`AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, `GOOGLE_MAPS_API_KEY`) are stored **exclusively** in environment variables on the backend.
* **No Frontend Exposure**: Provider keys are never sent in responses, HTML/DOM attributes, bundle outputs, or client headers.
* **Secure Photo Streaming Proxy**: Images from Google Places API are proxied via `/api/v1/travel/places/photos/{photo_name}` so client browsers never touch Google API keys.

### Environment Variables

```env
# Amadeus Self-Service API
AMADEUS_CLIENT_ID=your_amadeus_api_key
AMADEUS_CLIENT_SECRET=your_amadeus_api_secret
AMADEUS_BASE_URL=https://test.api.amadeus.com   # Production: https://api.amadeus.com

# Google Maps / Places API (New)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# Resilience & Caching
TRAVEL_CACHE_TTL_SECONDS=3600
TRAVEL_API_TIMEOUT_SECONDS=10.0
TRAVEL_API_MAX_RETRIES=2
TRAVEL_DEFAULT_PROVIDER=amadeus
```

---

## 3. Provider-Independent Internal Schemas

To prevent vendor lock-in and prevent proprietary response structures from leaking throughout the application, all providers convert raw payloads into standard Pydantic models:

### `TravelHotel`
```python
class TravelHotel(BaseModel):
    name: str
    hotel_id: Optional[str] = None
    chain_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    city_name: Optional[str] = None
    country_code: Optional[str] = None
    rating: Optional[float] = None
    price_tier: Optional[str] = None      # '₹', '₹₹', '₹₹₹'
    price: Optional[float] = None
    currency: str = "INR"
    amenities: List[str] = []
    photo_urls: List[str] = []
    provider: str                         # 'amadeus', 'google_places', 'local_db'
    provider_id: Optional[str] = None
    booking_url: Optional[str] = None
    metadata: Dict[str, Any] = {}
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
    provider: str                         # 'google_places', 'local_db'
    provider_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
```

### `TravelFlight`
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
    booking_url: Optional[str] = None
    provider: str = "amadeus"
```

### `TravelActivity`
```python
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
    booking_url: Optional[str] = None
    provider: str                         # 'amadeus', 'local_db'
    provider_id: Optional[str] = None
```

### `TravelAirport`
```python
class TravelAirport(BaseModel):
    name: str
    iata_code: str
    icao_code: Optional[str] = None
    city_name: Optional[str] = None
    country_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None
    provider: str                         # 'amadeus', 'local_db'
```

---

## 4. Provider Capabilities Matrix

| Capability | `AmadeusProvider` | `GooglePlacesProvider` | `LocalDatabaseProvider` (Fallback) |
| :--- | :---: | :---: | :---: |
| **Hotels by City/Coords** | Yes (Live inventory & offers) | No | Yes (Verified homestays & lodges) |
| **Flight Offers Search** | Yes (Live airline availability) | No | Yes (Regional transit connections) |
| **Activities & Tours** | Yes (Live experiences) | No | Yes (Indigenous workshops & walks) |
| **Airport Lookup** | Yes (Global IATA registry) | No | Yes (Regional airstrips & helipads) |
| **Place Search (POIs)** | No | Yes (Google Places New Search) | Yes (Curated local attractions) |
| **Place Details & Hours** | No | Yes (Full place profile) | Yes (Verified opening hours & fees) |
| **Search Autocomplete** | No | Yes (Predictive text matching) | Yes (Indexed destinations & tags) |
| **Photo Media Streaming** | No | Yes (Backend secure proxy) | Yes (Curated landscape media) |

---

## 5. Resilience, Fault Tolerance & Caching

### 1. Automatic Fallback to Local DB
If an external API:
* Has missing or invalid credentials
* Times out (`TRAVEL_API_TIMEOUT_SECONDS = 10.0`)
* Exceeds rate limits (`HTTP 429`)
* Returns internal server errors (`HTTP 5xx`)

The `TravelProviderService` catches the exception, logs diagnostic warnings, and **transparently serves local database entities**. The client never receives an unhandled 500 internal server error.

### 2. Rate-Limit Handling & Exponential Backoff
Requests to external endpoints are wrapped in a retry loop. If `HTTP 429` is received, the adapter applies exponential backoff:
$$\text{delay} = 2.0 \times 2^{\text{retry\_count}}$$
Retries up to `TRAVEL_API_MAX_RETRIES` before falling back.

### 3. Request Caching Layer (`TravelCacheManager`)
* **Deterministic Hashing**: Generates an MD5 signature from sorted request parameters (`travel:hotels:c3b1a89f...`).
* **TTL-based Invalidation**: Results are stored for `TRAVEL_CACHE_TTL_SECONDS` (default 1 hour).
* **Zero External Dependencies**: Operates with a thread-safe in-memory cache, with automatic Redis support if `REDIS_ENABLED=True`.

---

## 6. API Reference

All endpoints are registered under `/api/v1/travel`:

### 1. Search Hotels
`GET /api/v1/travel/hotels/search?city_code=DEL&radius_km=20`
`GET /api/v1/travel/hotels/search?latitude=27.595&longitude=93.838&radius_km=25`

### 2. Search Flights
`GET /api/v1/travel/flights/search?origin=DEL&destination=GAU&departure_date=2026-10-15&adults=1`

### 3. Search Activities
`GET /api/v1/travel/activities/search?latitude=27.595&longitude=93.838&radius_km=25`

### 4. Search Airports
`GET /api/v1/travel/airports/search?keyword=HGI`
`GET /api/v1/travel/airports/search?latitude=27.595&longitude=93.838`

### 5. Search Places (Google Places New)
`GET /api/v1/travel/places/search?query=Ziro+Valley+monastery`

### 6. Place Search Autocomplete
`GET /api/v1/travel/places/autocomplete?input_text=Ziro`

### 7. Place Details
`GET /api/v1/travel/places/details?place_id=ChIJN1t_tDeuEmsRUsoyG83frY4`

### 8. Secure Photo Proxy
`GET /api/v1/travel/places/photos/{photo_name}`

### 9. Provider Health Status
`GET /api/v1/travel/providers/status`
Returns:
```json
{
  "providers": {
    "amadeus": {
      "name": "Amadeus Travel Innovation API",
      "configured": false,
      "base_url": "https://test.api.amadeus.com",
      "capabilities": ["flights", "hotels", "activities", "airports"]
    },
    "google_places": {
      "name": "Google Places API (New)",
      "configured": false,
      "capabilities": ["places_search", "autocomplete", "details", "photos", "reviews"]
    },
    "local_db": {
      "name": "Local Database Provider (PostgreSQL / SQLite)",
      "configured": true,
      "capabilities": ["hotels", "places", "activities", "airports", "fallback"]
    }
  },
  "resilience": {
    "rate_limit_handling": "enabled",
    "provider_failure_fallback": "local_db",
    "timeout_seconds": 10.0,
    "max_retries": 2
  }
}
```
