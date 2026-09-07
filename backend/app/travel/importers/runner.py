"""CLI and programmatic runner for travel data seeding, sync, and provenance audit."""

import argparse
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.session import AsyncSessionFactory
from backend.app.models.destination import Destination, DestinationTag
from backend.app.travel.importers.external_adapters import WeatherAdapter, OverpassOSMAdapter
from backend.app.travel.importers.seed_data import SEED_DATA
from backend.app.travel.models.destination import DestinationCategory, Season, TravelTip
from backend.app.travel.models.geo import City, Country, State
from backend.app.travel.models.poi import Activity, Attraction, Hotel, Restaurant
from backend.app.travel.models.transit import Airport, TransportationOption, TravelRoute
from backend.app.travel.repositories.destination_repo import DestinationRepository
from backend.app.travel.repositories.geo_repo import GeoRepository
from backend.app.travel.repositories.poi_repo import POIRepository
from backend.app.travel.repositories.transit_repo import TransitRepository
from backend.app.travel.services.sync_service import SyncService


async def seed_travel_database(session: AsyncSession) -> Dict[str, int]:
    """Execute complete hierarchical seed of countries, states, cities, categories, destinations, and POIs."""
    geo_repo = GeoRepository(session)
    dest_repo = DestinationRepository(session)
    poi_repo = POIRepository(session)
    transit_repo = TransitRepository(session)

    stats = {
        "countries": 0,
        "states": 0,
        "cities": 0,
        "categories": 0,
        "airports": 0,
        "destinations": 0,
        "attractions": 0,
        "activities": 0,
        "hotels": 0,
        "restaurants": 0,
        "transportation_options": 0,
        "travel_routes": 0,
        "seasons": 0,
        "travel_tips": 0,
    }

    # 1. Countries
    country_map = {}
    for c_data in SEED_DATA.get("countries", []):
        country = await geo_repo.get_or_create_country(
            code=c_data["code"],
            name=c_data["name"],
            currency=c_data.get("currency", "INR"),
            phone_code=c_data.get("phone_code", "+91"),
            continent=c_data.get("continent", "Asia"),
            source=c_data.get("source", "seed_verified"),
            source_id=c_data.get("source_id"),
        )
        country_map[c_data["code"]] = country
        stats["countries"] += 1

    # 2. States
    state_map = {}
    for s_data in SEED_DATA.get("states", []):
        parent_country = country_map.get(s_data["country_code"])
        if not parent_country:
            continue
        state = await geo_repo.get_or_create_state(
            country_id=parent_country.id,
            name=s_data["name"],
            region=s_data["region"],
            code=s_data.get("code"),
            source=s_data.get("source", "seed_verified"),
            source_id=s_data.get("source_id"),
        )
        state_map[s_data["name"]] = state
        stats["states"] += 1

    # 3. Cities
    city_map = {}
    for ct_data in SEED_DATA.get("cities", []):
        parent_state = state_map.get(ct_data["state_name"])
        if not parent_state:
            continue
        city = await geo_repo.get_or_create_city(
            state_id=parent_state.id,
            name=ct_data["name"],
            city_code=ct_data.get("city_code"),
            latitude=ct_data.get("latitude"),
            longitude=ct_data.get("longitude"),
            elevation_meters=ct_data.get("elevation_meters"),
            source=ct_data.get("source", "seed_verified"),
            source_id=ct_data.get("source_id"),
        )
        city_map[ct_data["name"]] = city
        stats["cities"] += 1

    # 4. Destination Categories
    cat_map = {}
    for cat_data in SEED_DATA.get("categories", []):
        cat = await dest_repo.get_or_create_category(
            slug=cat_data["slug"],
            name=cat_data["name"],
            description=cat_data.get("description"),
            icon_name=cat_data.get("icon_name", "Compass"),
            source=cat_data.get("source", "seed_verified"),
            source_id=cat_data.get("source_id"),
        )
        cat_map[cat_data["slug"]] = cat
        stats["categories"] += 1

    # 5. Airports
    for a_data in SEED_DATA.get("airports", []):
        city = city_map.get(a_data.get("city_name"))
        await transit_repo.get_or_create_airport(
            iata_code=a_data["iata_code"],
            name=a_data["name"],
            city_id=city.id if city else None,
            icao_code=a_data.get("icao_code"),
            latitude=a_data.get("latitude"),
            longitude=a_data.get("longitude"),
            is_international=a_data.get("is_international", False),
            source=a_data.get("source", "seed_verified"),
            source_id=a_data.get("source_id"),
        )
        stats["airports"] += 1

    # 6. Destinations and related POIs
    for d_data in SEED_DATA.get("destinations", []):
        existing_stmt = select(Destination).where(Destination.slug == d_data["slug"])
        existing_res = await session.execute(existing_stmt)
        dest = existing_res.scalars().first()

        state_entity = state_map.get(d_data["state"])
        country_entity = country_map.get("IN")
        city_entity = city_map.get(d_data.get("city_name"))
        cat_entity = cat_map.get(d_data.get("category_slug"))

        if not dest:
            dest = Destination(
                slug=d_data["slug"],
                name=d_data["name"],
                state=d_data["state"],
                region=d_data["region"],
                category=d_data["category"],
                best_season=d_data["best_season"],
                budget=d_data["budget"],
                trust_score=d_data.get("trust_score", 90),
                description=d_data["description"],
                image_url=d_data["image_url"],
                latitude=d_data.get("latitude"),
                longitude=d_data.get("longitude"),
                is_hidden_gem=d_data.get("is_hidden_gem", True),
                accent_color=d_data.get("accent_color", "#5d6b43"),
                coordinate_x=d_data.get("coordinate_x", "50%"),
                coordinate_y=d_data.get("coordinate_y", "50%"),
                demo_note=d_data.get("demo_note", ""),
                country_id=country_entity.id if country_entity else None,
                state_id=state_entity.id if state_entity else None,
                city_id=city_entity.id if city_entity else None,
                category_id=cat_entity.id if cat_entity else None,
                source=d_data.get("source", "seed_verified"),
                source_id=d_data.get("source_id"),
                last_synced_at=datetime.now(timezone.utc),
            )
            session.add(dest)
            await session.flush()
            stats["destinations"] += 1
        else:
            # Update missing FK references if previously seeded with older schema
            if not dest.country_id and country_entity:
                dest.country_id = country_entity.id
            if not dest.state_id and state_entity:
                dest.state_id = state_entity.id
            if not dest.city_id and city_entity:
                dest.city_id = city_entity.id
            if not dest.category_id and cat_entity:
                dest.category_id = cat_entity.id
            if not dest.source:
                dest.source = "seed_verified"
                dest.source_id = f"dest/{dest.slug}"
                dest.last_synced_at = datetime.now(timezone.utc)
            stats["destinations"] += 1

        # Seed all child POIs, seasons, tips, transit idempotently
        await _seed_destination_children(
            session=session,
            dest=dest,
            d_data=d_data,
            city_entity=city_entity,
            dest_repo=dest_repo,
            poi_repo=poi_repo,
            transit_repo=transit_repo,
            stats=stats,
        )

    await session.commit()

    # Query total records across all travel tables for clear reporting
    total_stats = {
        "countries": (await session.execute(select(func.count(Country.id)))).scalar_one(),
        "states": (await session.execute(select(func.count(State.id)))).scalar_one(),
        "cities": (await session.execute(select(func.count(City.id)))).scalar_one(),
        "categories": (await session.execute(select(func.count(DestinationCategory.id)))).scalar_one(),
        "destinations": (await session.execute(select(func.count(Destination.id)))).scalar_one(),
        "airports": (await session.execute(select(func.count(Airport.id)))).scalar_one(),
        "seasons": (await session.execute(select(func.count(Season.id)))).scalar_one(),
        "travel_tips": (await session.execute(select(func.count(TravelTip.id)))).scalar_one(),
        "attractions": (await session.execute(select(func.count(Attraction.id)))).scalar_one(),
        "activities": (await session.execute(select(func.count(Activity.id)))).scalar_one(),
        "hotels": (await session.execute(select(func.count(Hotel.id)))).scalar_one(),
        "restaurants": (await session.execute(select(func.count(Restaurant.id)))).scalar_one(),
        "transportation_options": (await session.execute(select(func.count(TransportationOption.id)))).scalar_one(),
        "travel_routes": (await session.execute(select(func.count(TravelRoute.id)))).scalar_one(),
    }
    return total_stats


async def _seed_destination_children(
    session: AsyncSession,
    dest: Destination,
    d_data: Dict[str, Any],
    city_entity: Optional[City],
    dest_repo: DestinationRepository,
    poi_repo: POIRepository,
    transit_repo: TransitRepository,
    stats: Dict[str, int],
) -> None:
    """Seed all child entities (tags, seasons, tips, attractions, activities, hotels, restaurants, transit) idempotently."""
    # 1. Tags
    existing_tags_res = await session.execute(
        select(DestinationTag.tag).where(DestinationTag.destination_id == dest.id)
    )
    existing_tags = set(existing_tags_res.scalars().all())
    for t in d_data.get("tags", []):
        if t not in existing_tags:
            session.add(DestinationTag(destination_id=dest.id, tag=t))
            existing_tags.add(t)

    # 2. Seasons
    existing_seasons_res = await session.execute(
        select(Season.season_name).where(Season.destination_id == dest.id)
    )
    existing_seasons = set(existing_seasons_res.scalars().all())
    for s in d_data.get("seasons", []):
        if s["season_name"] not in existing_seasons:
            await dest_repo.add_season(
                destination_id=dest.id,
                season_name=s["season_name"],
                start_month=s["start_month"],
                end_month=s["end_month"],
                weather_summary=s["weather_summary"],
                avg_temp_min_c=s.get("avg_temp_min_c"),
                avg_temp_max_c=s.get("avg_temp_max_c"),
                rainfall_level=s.get("rainfall_level", "moderate"),
                is_recommended=s.get("is_recommended", True),
                advisory_notes=s.get("advisory_notes"),
                source="seed_verified",
                source_id=f"season/{dest.slug}/{s['season_name'].lower().replace(' ', '_')}",
            )
            existing_seasons.add(s["season_name"])
            stats["seasons"] += 1

    # 3. Tips
    existing_tips_res = await session.execute(
        select(TravelTip.title).where(TravelTip.destination_id == dest.id)
    )
    existing_tips = set(existing_tips_res.scalars().all())
    for tip in d_data.get("tips", []):
        if tip["title"] not in existing_tips:
            await dest_repo.add_travel_tip(
                destination_id=dest.id,
                category=tip.get("category", "logistics"),
                title=tip["title"],
                content=tip["content"],
                priority=tip.get("priority", 1),
                source="seed_verified",
                source_id=f"tip/{dest.slug}/{tip['title'][:20].lower().replace(' ', '_')}",
            )
            existing_tips.add(tip["title"])
            stats["travel_tips"] += 1

    # 4. Attractions
    existing_attractions_res = await session.execute(
        select(Attraction.name).where(Attraction.destination_id == dest.id)
    )
    existing_attractions = set(existing_attractions_res.scalars().all())
    for attr in d_data.get("attractions", []):
        if attr["name"] not in existing_attractions:
            await poi_repo.create_attraction(
                destination_id=dest.id,
                city_id=city_entity.id if city_entity else None,
                name=attr["name"],
                category=attr["category"],
                description=attr["description"],
                latitude=attr.get("latitude"),
                longitude=attr.get("longitude"),
                entry_fee=attr.get("entry_fee", "Free"),
                timings=attr.get("timings", "Daylight hours"),
                difficulty=attr.get("difficulty", "Easy"),
                recommended_duration_mins=attr.get("recommended_duration_mins", 120),
                tags=attr.get("tags", []),
                source="seed_verified",
                source_id=f"attr/{dest.slug}/{attr['name'].lower().replace(' ', '_')}",
            )
            existing_attractions.add(attr["name"])
            stats["attractions"] += 1

    # 5. Activities
    existing_activities_res = await session.execute(
        select(Activity.title).where(Activity.destination_id == dest.id)
    )
    existing_activities = set(existing_activities_res.scalars().all())
    for act in d_data.get("activities", []):
        if act["title"] not in existing_activities:
            await poi_repo.create_activity(
                destination_id=dest.id,
                city_id=city_entity.id if city_entity else None,
                title=act["title"],
                activity_type=act["activity_type"],
                description=act["description"],
                duration_hours=act.get("duration_hours", 2.5),
                price_range=act.get("price_range", "₹500"),
                seasonality=act.get("seasonality", "All year"),
                guide_required=act.get("guide_required", True),
                source="seed_verified",
                source_id=f"act/{dest.slug}/{act['title'][:20].lower().replace(' ', '_')}",
            )
            existing_activities.add(act["title"])
            stats["activities"] += 1

    # 6. Hotels
    existing_hotels_res = await session.execute(
        select(Hotel.name).where(Hotel.destination_id == dest.id)
    )
    existing_hotels = set(existing_hotels_res.scalars().all())
    for h in d_data.get("hotels", []):
        if h["name"] not in existing_hotels:
            await poi_repo.create_hotel(
                destination_id=dest.id,
                city_id=city_entity.id if city_entity else None,
                name=h["name"],
                stay_type=h.get("stay_type", "Homestay"),
                address=h["address"],
                latitude=h.get("latitude"),
                longitude=h.get("longitude"),
                price_per_night=h.get("price_per_night", "₹1,500 – ₹2,500"),
                price_level=h.get("price_level", "₹₹"),
                rating=h.get("rating", 4.7),
                amenities=h.get("amenities", []),
                sustainability_rating=h.get("sustainability_rating", 90),
                source="seed_verified",
                source_id=f"hotel/{dest.slug}/{h['name'].lower().replace(' ', '_')}",
            )
            existing_hotels.add(h["name"])
            stats["hotels"] += 1

    # 7. Restaurants
    existing_restaurants_res = await session.execute(
        select(Restaurant.name).where(Restaurant.destination_id == dest.id)
    )
    existing_restaurants = set(existing_restaurants_res.scalars().all())
    for r in d_data.get("restaurants", []):
        if r["name"] not in existing_restaurants:
            await poi_repo.create_restaurant(
                destination_id=dest.id,
                city_id=city_entity.id if city_entity else None,
                name=r["name"],
                cuisine_type=r["cuisine_type"],
                address=r["address"],
                latitude=r.get("latitude"),
                longitude=r.get("longitude"),
                price_range=r.get("price_range", "₹"),
                rating=r.get("rating", 4.5),
                must_try_dishes=r.get("must_try_dishes", []),
                opening_hours=r.get("opening_hours", "11:00 AM – 08:30 PM"),
                source="seed_verified",
                source_id=f"rest/{dest.slug}/{r['name'].lower().replace(' ', '_')}",
            )
            existing_restaurants.add(r["name"])
            stats["restaurants"] += 1

    # 8. Transportation options
    existing_trans_res = await session.execute(
        select(TransportationOption.transport_type, TransportationOption.origin_name).where(
            TransportationOption.destination_id == dest.id
        )
    )
    existing_trans = {(row[0], row[1]) for row in existing_trans_res.all()}
    for opt in d_data.get("transportation_options", []):
        pair = (opt["transport_type"], opt["origin_name"])
        if pair not in existing_trans:
            await transit_repo.create_transportation_option(
                destination_id=dest.id,
                transport_type=opt["transport_type"],
                origin_name=opt["origin_name"],
                destination_name=opt["destination_name"],
                duration_hours=opt["duration_hours"],
                cost_estimate=opt["cost_estimate"],
                frequency=opt.get("frequency", "Daily"),
                operator_name=opt.get("operator_name"),
                booking_tips=opt.get("booking_tips"),
                source="seed_verified",
                source_id=f"transport/{dest.slug}/{opt['transport_type'].lower().replace(' ', '_')}",
            )
            existing_trans.add(pair)
            stats["transportation_options"] += 1

    # 9. Travel Routes
    existing_routes_res = await session.execute(
        select(TravelRoute.route_name).where(TravelRoute.destination_id == dest.id)
    )
    existing_routes = set(existing_routes_res.scalars().all())
    for tr in d_data.get("travel_routes", []):
        if tr["route_name"] not in existing_routes:
            await transit_repo.create_travel_route(
                destination_id=dest.id,
                origin_city_id=city_entity.id if city_entity else None,
                route_name=tr["route_name"],
                mode=tr.get("mode", "Road"),
                distance_km=tr["distance_km"],
                typical_duration_hours=tr["typical_duration_hours"],
                road_condition=tr.get("road_condition", ""),
                scenic_rating=tr.get("scenic_rating", 9),
                seasonal_notes=tr.get("seasonal_notes"),
                source="seed_verified",
                source_id=f"route/{dest.slug}/{tr['route_name'][:20].lower().replace(' ', '_')}",
            )
            existing_routes.add(tr["route_name"])
            stats["travel_routes"] += 1


async def main():
    parser = argparse.ArgumentParser(description="KHOJAI Travel Data Layer Runner")
    parser.add_argument("--seed", action="store_true", help="Seed database with verified Indian travel entities")
    parser.add_argument("--audit", action="store_true", help="Audit database provenance and staleness")
    args = parser.parse_args()

    async with AsyncSessionFactory() as session:
        if args.seed:
            print("Seeding travel database with curated Indian travel intelligence...")
            stats = await seed_travel_database(session)
            print("Seeding complete! Summary:")
            for k, v in stats.items():
                print(f"  - {k}: {v}")

        if args.audit:
            print("\nAuditing data provenance and freshness...")
            sync_svc = SyncService(session)
            dest_audit = await sync_svc.audit_staleness(Destination)
            print(f"Destinations: {dest_audit}")


if __name__ == "__main__":
    asyncio.run(main())
