"""Comprehensive unit and integration test suite for KHOJAI Scalable Travel Data Layer.

Covers:
1. All 18 Models & Entity Integrity (UUIDs, Coordinates, Provenance, Metadata)
2. Hierarchy & Relationships (Country -> State -> City -> POIs/Transit, Trip -> TripDay -> TripItem, User -> UserTravelPreference)
3. Check Constraints & Validation
4. Repositories (Geo, Destination, POI, Transit, Trip)
5. Services (CatalogService, HybridTravelRouter, SyncService)
6. Importers & External Adapters (BaseTravelImporter, WeatherAdapter, OverpassOSMAdapter, WikidataAdapter, Seed Runner)
"""

import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.app.models.destination import Destination, DestinationTag, TrustMetric
from backend.app.models.user import User
from backend.app.travel.importers.base import BaseTravelImporter, ProvenanceRecord
from backend.app.travel.importers.external_adapters import (
    OverpassOSMAdapter,
    WeatherAdapter,
    WikidataAdapter,
)
from backend.app.travel.importers.runner import seed_travel_database
from backend.app.travel.models.destination import DestinationCategory, Season, TravelTip
from backend.app.travel.models.geo import City, Country, State
from backend.app.travel.models.poi import Activity, Attraction, Hotel, Restaurant
from backend.app.travel.models.transit import Airport, TransportationOption, TravelRoute
from backend.app.travel.models.trip import Trip, TripDay, TripItem, UserTravelPreference
from backend.app.travel.repositories.destination_repo import DestinationRepository
from backend.app.travel.repositories.geo_repo import GeoRepository
from backend.app.travel.repositories.poi_repo import POIRepository
from backend.app.travel.repositories.transit_repo import TransitRepository
from backend.app.travel.repositories.trip_repo import TripRepository
from backend.app.travel.services.catalog_service import CatalogService
from backend.app.travel.services.hybrid_router import HybridTravelRouter
from backend.app.travel.services.sync_service import SyncService


# ============================================================================
# 1. Geographic Hierarchy: Country -> State -> City
# ============================================================================

@pytest.mark.asyncio
async def test_geographic_hierarchy_creation(db_session):
    """Test sovereign Country -> State -> City relationships with UUIDs and provenance."""
    country = Country(
        code="IN",
        name="India",
        currency="INR",
        phone_code="+91",
        continent="Asia",
        source="seed_verified",
        source_id="ISO-3166-IN",
        last_synced_at=datetime.now(timezone.utc),
    )
    db_session.add(country)
    await db_session.flush()

    assert isinstance(country.id, uuid.UUID)
    assert country.code == "IN"
    assert country.source == "seed_verified"

    state = State(
        country_id=country.id,
        name="Arunachal Pradesh",
        code="AR",
        region="Northeast",
        source="seed_verified",
        source_id="ISO-3166-2:IN-AR",
    )
    db_session.add(state)
    await db_session.flush()

    assert state.country_id == country.id
    assert state.region == "Northeast"

    city = City(
        state_id=state.id,
        name="Naharlagun",
        city_code="NHLN",
        latitude=27.1064,
        longitude=93.6934,
        elevation_meters=290,
        source="seed_verified",
        source_id="geo/nhln",
    )
    db_session.add(city)
    await db_session.commit()

    # Verify query and loaded relationships
    geo_repo = GeoRepository(db_session)
    fetched_city = await geo_repo.get_city_by_id(city.id)
    assert fetched_city is not None
    assert fetched_city.name == "Naharlagun"
    assert fetched_city.state.name == "Arunachal Pradesh"
    assert fetched_city.latitude == 27.1064
    assert fetched_city.longitude == 93.6934


# ============================================================================
# 2. Destination & Classification Taxonomy
# ============================================================================

@pytest.mark.asyncio
async def test_destination_and_taxonomy(db_session):
    """Test DestinationCategory, Destination, Season, and TravelTip."""
    cat = DestinationCategory(
        slug="living-heritage-cultural-landscape",
        name="Living Heritage & Cultural Landscape",
        description="Traditional tribal landscapes",
        icon_name="Landmark",
    )
    db_session.add(cat)
    await db_session.flush()

    dest = Destination(
        slug="ziro-valley-test",
        name="Ziro Valley Test",
        category_id=cat.id,
        state="Arunachal Pradesh",
        region="Northeast",
        category="Living Heritage & Cultural Landscape",
        best_season="Sep – Nov",
        budget="₹₹",
        trust_score=94,
        description="Apatani cultural heartland with pine ridges and fish-paddy farming.",
        image_url="https://images.unsplash.com/photo-ziro",
        latitude=27.5950,
        longitude=93.8385,
        is_hidden_gem=True,
        source="curated_editorial",
        source_id="dest/ziro",
        last_synced_at=datetime.now(timezone.utc),
    )
    db_session.add(dest)
    await db_session.flush()

    season = Season(
        destination_id=dest.id,
        season_name="Autumn Harvest",
        start_month=9,
        end_month=11,
        weather_summary="Golden rice fields and crisp air.",
        avg_temp_min_c=8.0,
        avg_temp_max_c=22.0,
        rainfall_level="low",
        is_recommended=True,
    )
    tip = TravelTip(
        destination_id=dest.id,
        category="logistics",
        title="Inner Line Permit Required",
        content="Obtain ILP online prior to crossing Arunachal border at Banderdewa.",
        priority=1,
    )
    db_session.add_all([season, tip])
    await db_session.commit()

    dest_repo = DestinationRepository(db_session)
    loaded_dest = await dest_repo.get_by_slug("ziro-valley-test")
    assert loaded_dest is not None
    assert len(loaded_dest.seasons) == 1
    assert loaded_dest.seasons[0].season_name == "Autumn Harvest"
    assert len(loaded_dest.travel_tips) == 1
    assert loaded_dest.travel_tips[0].priority == 1


# ============================================================================
# 3. Points of Interest (POIs): Attraction, Activity, Hotel, Restaurant
# ============================================================================

@pytest.mark.asyncio
async def test_pois_and_provenance(db_session):
    """Test Attraction, Activity, Hotel, and Restaurant with ratings, pricing, and coordinates."""
    dest = Destination(
        slug="poi-test-dest",
        name="POI Test Destination",
        state="Assam",
        region="Northeast",
        category="Riverine Island",
        best_season="Nov – Feb",
        budget="₹",
        trust_score=88,
        description="World's largest river island on the Brahmaputra.",
        image_url="https://images.unsplash.com/photo-majuli",
    )
    db_session.add(dest)
    await db_session.flush()

    # Attraction
    attraction = Attraction(
        destination_id=dest.id,
        name="Kamalabari Satra",
        category="Neo-Vaishnavite Monastery",
        description="Center of classical music, dance, and bamboo craftsmanship.",
        latitude=26.9540,
        longitude=94.1620,
        entry_fee="Free",
        timings="06:00 AM – 06:00 PM",
        difficulty="Easy",
        recommended_duration_mins=90,
        tags=["Heritage", "Culture"],
        source="seed_verified",
        source_id="attr/kamalabari",
    )
    # Activity
    activity = Activity(
        destination_id=dest.id,
        title="Traditional Majuli Mask-Making Workshop",
        activity_type="Cultural Workshop",
        description="Hands-on demonstration using bamboo frames and cow dung clay.",
        duration_hours=2.5,
        price_range="₹300 – ₹500",
        seasonality="Oct – Mar",
        guide_required=True,
        source="seed_verified",
        source_id="act/mask-making",
    )
    # Hotel / Homestay
    hotel = Hotel(
        destination_id=dest.id,
        name="La Maison de Ananda",
        stay_type="Homestay",
        address="Kharjan Village, Majuli",
        latitude=26.9601,
        longitude=94.1702,
        price_per_night="₹1,200 – ₹1,800",
        price_level="₹₹",
        rating=4.8,
        amenities=["Bamboo cottage", "Traditional Mishing meals"],
        sustainability_rating=92,
        source="seed_verified",
        source_id="hotel/ananda",
    )
    # Restaurant / Traditional Hearth
    restaurant = Restaurant(
        destination_id=dest.id,
        name="Ushapur Tribal Hearth",
        cuisine_type="Mishing Tribal",
        address="Kamalabari Road, Majuli",
        latitude=26.9555,
        longitude=94.1650,
        price_range="₹",
        rating=4.6,
        must_try_dishes=["Bamboo shoot pork", "Apin sticky rice", "Poro apong"],
        opening_hours="11:30 AM – 08:30 PM",
        source="seed_verified",
        source_id="rest/ushapur",
    )

    db_session.add_all([attraction, activity, hotel, restaurant])
    await db_session.commit()

    poi_repo = POIRepository(db_session)
    attractions = await poi_repo.list_attractions_by_destination(dest.id)
    assert len(attractions) == 1
    assert attractions[0].name == "Kamalabari Satra"
    assert attractions[0].tags == ["Heritage", "Culture"]

    hotels = await poi_repo.list_hotels_by_destination(dest.id)
    assert len(hotels) == 1
    assert hotels[0].stay_type == "Homestay"
    assert hotels[0].rating == 4.8
    assert hotels[0].sustainability_rating == 92


# ============================================================================
# 4. Transit Connectivity: Airport, TransportationOption, TravelRoute
# ============================================================================

@pytest.mark.asyncio
async def test_transit_connectivity(db_session):
    """Test Airport, TransportationOption, and TravelRoute."""
    dest = Destination(
        slug="transit-test-dest",
        name="Transit Test Destination",
        state="Himachal Pradesh",
        region="Himalayas",
        category="Alpine Valley",
        best_season="Mar – Jun",
        budget="₹₹",
        trust_score=90,
        description="Gateway to Great Himalayan National Park.",
        image_url="https://images.unsplash.com/photo-tirthan",
    )
    db_session.add(dest)
    await db_session.flush()

    # Airport
    airport = Airport(
        name="Kullu-Manali Airport (Bhuntar)",
        iata_code="KUU",
        icao_code="VIBR",
        latitude=31.8767,
        longitude=77.1542,
        is_international=False,
        source="seed_verified",
        source_id="airport/kuu",
    )
    # Transportation option
    transport = TransportationOption(
        destination_id=dest.id,
        transport_type="Private Cab",
        origin_name="Bhuntar Airport",
        destination_name="Gushaini / Tirthan Valley",
        duration_hours=2.0,
        cost_estimate="₹1,800 – ₹2,400",
        frequency="On demand",
        booking_tips="Book official taxi counter at Bhuntar airport exit.",
        source="seed_verified",
        source_id="transport/kuu-tirthan",
    )
    # Scenic travel route
    route = TravelRoute(
        destination_id=dest.id,
        route_name="Chandigarh to Tirthan via Aut Tunnel",
        mode="Road",
        distance_km=270.0,
        typical_duration_hours=7.5,
        road_condition="Four-lane till Kiratpur, then smooth winding hill highway.",
        scenic_rating=9,
        seasonal_notes="Expect monsoon slowdowns July-August.",
        source="seed_verified",
        source_id="route/chandigarh-tirthan",
    )

    db_session.add_all([airport, transport, route])
    await db_session.commit()

    transit_repo = TransitRepository(db_session)
    fetched_airport = await transit_repo.get_airport_by_iata("KUU")
    assert fetched_airport is not None
    assert fetched_airport.iata_code == "KUU"

    routes = await transit_repo.list_routes_by_destination(dest.id)
    assert len(routes) == 1
    assert routes[0].scenic_rating == 9
    assert routes[0].distance_km == 270.0


# ============================================================================
# 5. Trip Planning & Cascade Deletion: Trip -> TripDay -> TripItem
# ============================================================================

@pytest.mark.asyncio
async def test_trip_planning_and_cascade_deletion(db_session):
    """Test Trip creation, sequenced TripDays and TripItems, and cascade deletion."""
    user = User(
        email="travelplanner@khojai.in",
        hashed_password="hashed_secure_pass",
        full_name="Arun Kumar",
    )
    db_session.add(user)
    await db_session.flush()

    trip = Trip(
        user_id=user.id,
        title="4 Days in Ziro Valley",
        description="Cultural exploration and gentle walking trails.",
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 14),
        total_days=4,
        budget_tier="₹₹",
        status="confirmed",
        is_public=True,
    )
    db_session.add(trip)
    await db_session.flush()

    assert trip.share_token is not None
    assert len(trip.share_token) >= 8

    day1 = TripDay(
        trip_id=trip.id,
        day_number=1,
        day_date=date(2026, 10, 10),
        theme_title="Arrival & Hong Village Welcome",
        notes="Check in to homestay, evening hearth tea.",
    )
    db_session.add(day1)
    await db_session.flush()

    item1 = TripItem(
        trip_day_id=day1.id,
        item_type="hotel",
        title="Check in to Donyi Hango Homestay",
        start_time="02:00 PM",
        end_time="03:00 PM",
        sort_order=1,
    )
    item2 = TripItem(
        trip_day_id=day1.id,
        item_type="activity",
        title="Guided walk across Hong Village lapangs",
        start_time="03:30 PM",
        end_time="05:30 PM",
        sort_order=2,
    )
    db_session.add_all([item1, item2])
    await db_session.commit()

    trip_repo = TripRepository(db_session)
    fetched_trip = await trip_repo.get_by_share_token(trip.share_token)
    assert fetched_trip is not None
    assert len(fetched_trip.days) == 1
    assert len(fetched_trip.days[0].items) == 2
    assert fetched_trip.days[0].items[0].title == "Check in to Donyi Hango Homestay"

    # Verify Cascade Deletion: deleting trip removes days and items
    await trip_repo.delete_trip(trip.id)
    await db_session.commit()

    remaining_days = await db_session.execute(select(TripDay).where(TripDay.trip_id == trip.id))
    assert len(remaining_days.scalars().all()) == 0

    remaining_items = await db_session.execute(select(TripItem).where(TripItem.trip_day_id == day1.id))
    assert len(remaining_items.scalars().all()) == 0


# ============================================================================
# 6. UserTravelPreference (1:1 Relationship with User)
# ============================================================================

@pytest.mark.asyncio
async def test_user_travel_preference_one_to_one(db_session):
    """Test 1:1 User to UserTravelPreference relationship and constraints."""
    user = User(
        email="preferencetest@khojai.in",
        hashed_password="hashed_secure_pass",
        full_name="Meera Sen",
    )
    db_session.add(user)
    await db_session.flush()

    pref = UserTravelPreference(
        user_id=user.id,
        budget_preference="₹₹",
        preferred_pace="unhurried",
        travel_styles=["Slow travel", "Culture-led"],
        dietary_needs="strictly_vegetarian",
        fitness_level="moderate",
        preferred_stay_types=["Homestay", "Eco-Lodge"],
        preferred_regions=["Northeast", "Himalayas"],
    )
    db_session.add(pref)
    await db_session.commit()

    # Re-query user and check relationship
    result = await db_session.execute(select(User).where(User.id == user.id))
    fetched_user = result.scalars().first()
    await db_session.refresh(fetched_user, ["travel_preference"])

    assert fetched_user.travel_preference is not None
    assert fetched_user.travel_preference.preferred_pace == "unhurried"
    assert fetched_user.travel_preference.dietary_needs == "strictly_vegetarian"


# ============================================================================
# 7. Check Constraints Enforcement
# ============================================================================

@pytest.mark.asyncio
async def test_season_month_check_constraint(db_session):
    """Test ck_seasons_start_month constraint rejects month > 12."""
    dest = Destination(
        slug="constraint-test-dest",
        name="Constraint Test Dest",
        state="Arunachal Pradesh",
        region="Northeast",
        category="Nature",
        best_season="Oct",
        budget="₹",
        trust_score=80,
        description="Testing check constraints",
        image_url="/test.jpg",
    )
    db_session.add(dest)
    await db_session.flush()

    invalid_season = Season(
        destination_id=dest.id,
        season_name="Invalid Month Season",
        start_month=13,  # Invalid! Must be 1-12
        end_month=5,
        weather_summary="Test invalid summary",
    )
    db_session.add(invalid_season)

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


# ============================================================================
# 8. Sync Service & Staleness Auditing
# ============================================================================

@pytest.mark.asyncio
async def test_sync_service_audit_and_stamping(db_session):
    """Test SyncService.audit_staleness and mark_synced."""
    # Add fresh destination
    fresh_dest = Destination(
        slug="fresh-dest",
        name="Fresh Destination",
        state="Sikkim",
        region="Northeast",
        category="Culture",
        best_season="Apr",
        budget="₹₹",
        trust_score=85,
        description="Freshly verified destination.",
        image_url="/fresh.jpg",
        source="seed_verified",
        last_synced_at=datetime.now(timezone.utc),
    )
    # Add stale destination
    stale_dest = Destination(
        slug="stale-dest",
        name="Stale Destination",
        state="Sikkim",
        region="Northeast",
        category="Culture",
        best_season="Apr",
        budget="₹₹",
        trust_score=85,
        description="Destination synced 120 days ago.",
        image_url="/stale.jpg",
        source="osm_overpass",
        last_synced_at=datetime.now(timezone.utc) - timedelta(days=120),
    )
    db_session.add_all([fresh_dest, stale_dest])
    await db_session.commit()

    sync_service = SyncService(db_session)
    audit = await sync_service.audit_staleness(Destination, max_age_days=90)

    assert audit["entity_name"] == "destinations"
    assert audit["total_records"] >= 2
    assert audit["stale_records"] >= 1
    assert "freshness_ratio" in audit

    # Mark stale entity synced
    await sync_service.mark_synced(stale_dest, source="curated_audit")
    await db_session.commit()

    assert stale_dest.source == "curated_audit"
    assert stale_dest.last_synced_at is not None
    assert (datetime.now(timezone.utc) - stale_dest.last_synced_at).total_seconds() < 5


# ============================================================================
# 9. Hybrid Travel Router (3-Tier Context Resolution)
# ============================================================================

@pytest.mark.asyncio
async def test_hybrid_travel_router_coordination(db_session):
    """Test HybridTravelRouter combining Tier 1 local DB + Tier 2 live APIs + Tier 3 AI synthesis."""
    dest = Destination(
        slug="hybrid-router-test",
        name="Hybrid Router Valley",
        state="Arunachal Pradesh",
        region="Northeast",
        category="Offbeat",
        best_season="Oct – Nov",
        budget="₹₹",
        trust_score=92,
        description="Remote tranquil valley for quiet travel.",
        image_url="/valley.jpg",
        latitude=27.5950,
        longitude=93.8385,
        source="seed_verified",
        source_id="dest/hybrid-test",
        last_synced_at=datetime.now(timezone.utc),
    )
    db_session.add(dest)
    await db_session.commit()

    router = HybridTravelRouter(db_session)
    # Request destination context with weather disabled to avoid external HTTP dependency during unit tests
    context = await router.resolve_destination_context(
        slug_or_id="hybrid-router-test",
        include_live_weather=False,
        include_live_transit=False,
    )

    assert "tier1_local_database" in context
    assert context["tier1_local_database"]["name"] == "Hybrid Router Valley"
    assert context["tier1_local_database"]["trust_score"] == 92

    assert "tier3_ai_knowledge_rag" in context
    rag_context = context["tier3_ai_knowledge_rag"]
    assert "Verified destination 'Hybrid Router Valley'" in rag_context["synthesis_summary"]
    assert rag_context["cultural_narrative"] == "Remote tranquil valley for quiet travel."
    assert rag_context["data_freshness"]["source"] == "seed_verified"


# ============================================================================
# 10. External Adapters & Copyright Compliance
# ============================================================================

def test_provenance_record_and_copyright_compliance():
    """Verify ProvenanceRecord enforces non-copyrighted factual data assertion."""
    importer = WeatherAdapter()
    provenance = importer.validate_provenance(source_id="coords/27.595,93.8385")

    assert provenance.source == "open_meteo"
    assert provenance.source_id == "coords/27.595,93.8385"
    assert provenance.is_copyright_compliant is True
    assert isinstance(provenance.last_synced_at, datetime)


@pytest.mark.asyncio
async def test_weather_adapter_input_validation():
    """Test WeatherAdapter validates required lat/lon parameters."""
    adapter = WeatherAdapter()
    with pytest.raises(ValueError, match="lat and lon are required"):
        await adapter.import_data(lat=None, lon=93.8)


@pytest.mark.asyncio
async def test_overpass_adapter_input_validation():
    """Test OverpassOSMAdapter validates required coordinates."""
    adapter = OverpassOSMAdapter()
    with pytest.raises(ValueError, match="lat and lon are required"):
        await adapter.import_data(lat=27.5, lon=None)


@pytest.mark.asyncio
async def test_wikidata_adapter_input_validation():
    """Test WikidataAdapter validates required entity ID."""
    adapter = WikidataAdapter()
    with pytest.raises(ValueError, match="wikidata_id is required"):
        await adapter.import_data(wikidata_id="")


# ============================================================================
# 11. End-to-End Seed Runner Execution
# ============================================================================

@pytest.mark.asyncio
async def test_seed_travel_database_end_to_end(db_session):
    """Test that seed_travel_database populates complete curated Indian travel layer."""
    stats = await seed_travel_database(db_session)

    # Verify counts for all essential travel entities
    assert stats["countries"] >= 1
    assert stats["states"] >= 3
    assert stats["cities"] >= 3
    assert stats["categories"] >= 3
    assert stats["destinations"] >= 3
    assert stats["airports"] >= 3
    assert stats["attractions"] >= 3
    assert stats["activities"] >= 3
    assert stats["hotels"] >= 3
    assert stats["restaurants"] >= 3
    assert stats["transportation_options"] >= 3
    assert stats["travel_routes"] >= 3
    assert stats["seasons"] >= 3
    assert stats["travel_tips"] >= 3
