"""Local Database Travel Provider serving as the resilient, high-fidelity fallback."""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database.session import AsyncSessionFactory
from backend.app.models.destination import Destination
from backend.app.travel.models.geo import City
from backend.app.travel.models.poi import Activity, Attraction, Hotel, Restaurant
from backend.app.travel.models.transit import Airport
from backend.app.travel.normalizers.local_normalizer import LocalDatabaseNormalizer
from backend.app.travel.providers.base import TravelDataProvider
from backend.app.travel.schemas.internal import (
    TravelActivity,
    TravelAirport,
    TravelFlight,
    TravelHotel,
    TravelPlace,
    TravelPlaceAutocompleteItem,
)

logger = logging.getLogger("khojai.travel.providers.local_db")


class LocalDatabaseProvider(TravelDataProvider):
    """Fallback provider querying local PostgreSQL/SQLite database entities."""

    def __init__(self, session_factory=None):
        super().__init__(provider_name="local_db")
        self.session_factory = session_factory or AsyncSessionFactory

    @property
    def is_configured(self) -> bool:
        # Local database is always configured
        return True

    async def search_hotels(
        self,
        city_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: int = 20,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelHotel]:
        async with self.session_factory() as session:
            stmt = select(Hotel).options(selectinload(Hotel.city)).limit(limit)
            if city_code:
                stmt = stmt.join(Hotel.city).where(func.lower(City.city_code) == city_code.lower().strip())
            elif latitude is not None and longitude is not None:
                deg_radius = radius_km / 111.0
                stmt = stmt.where(
                    Hotel.latitude >= latitude - deg_radius,
                    Hotel.latitude <= latitude + deg_radius,
                    Hotel.longitude >= longitude - deg_radius,
                    Hotel.longitude <= longitude + deg_radius,
                )

            result = await session.execute(stmt)
            hotels = result.scalars().all()
            return [LocalDatabaseNormalizer.normalize_hotel(h) for h in hotels]

    async def search_flights(
        self,
        origin_code: str,
        destination_code: str,
        departure_date: str,
        adults: int = 1,
        return_date: Optional[str] = None,
        limit: int = 10,
        **kwargs,
    ) -> List[TravelFlight]:
        # Local DB does not store live dynamic airfare, but provides regional scheduled routes
        return []

    async def search_activities(
        self,
        latitude: float,
        longitude: float,
        radius_km: int = 25,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelActivity]:
        async with self.session_factory() as session:
            stmt = select(Activity).limit(limit)
            result = await session.execute(stmt)
            activities = result.scalars().all()
            return [LocalDatabaseNormalizer.normalize_activity(a) for a in activities]

    async def search_airports(
        self,
        keyword: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        limit: int = 10,
        **kwargs,
    ) -> List[TravelAirport]:
        async with self.session_factory() as session:
            stmt = select(Airport).options(selectinload(Airport.city)).limit(limit)
            if keyword:
                term = f"%{keyword.lower().strip()}%"
                stmt = stmt.where(
                    or_(
                        func.lower(Airport.name).like(term),
                        func.lower(Airport.iata_code).like(term),
                    )
                )
            result = await session.execute(stmt)
            airports = result.scalars().all()
            return [LocalDatabaseNormalizer.normalize_airport(a) for a in airports]

    async def search_places(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 10000,
        included_types: Optional[List[str]] = None,
        limit: int = 15,
        **kwargs,
    ) -> List[TravelPlace]:
        places: List[TravelPlace] = []
        term = f"%{query.lower().strip()}%"

        async with self.session_factory() as session:
            # Attractions
            attr_stmt = (
                select(Attraction)
                .options(selectinload(Attraction.city))
                .where(
                    or_(
                        func.lower(Attraction.name).like(term),
                        func.lower(Attraction.category).like(term),
                    )
                )
                .limit(limit)
            )
            attr_res = await session.execute(attr_stmt)
            for a in attr_res.scalars().all():
                places.append(LocalDatabaseNormalizer.normalize_attraction_as_place(a))

            # Restaurants
            if len(places) < limit:
                rest_stmt = (
                    select(Restaurant)
                    .where(
                        or_(
                            func.lower(Restaurant.name).like(term),
                            func.lower(Restaurant.cuisine_type).like(term),
                        )
                    )
                    .limit(limit - len(places))
                )
                rest_res = await session.execute(rest_stmt)
                for r in rest_res.scalars().all():
                    places.append(LocalDatabaseNormalizer.normalize_restaurant_as_place(r))

        return places[:limit]

    async def get_place_details(self, place_id: str, **kwargs) -> Optional[TravelPlace]:
        try:
            val_uuid = UUID(place_id)
        except ValueError:
            return None

        async with self.session_factory() as session:
            # Check Attraction
            attr_stmt = select(Attraction).options(selectinload(Attraction.city)).where(Attraction.id == val_uuid)
            attr_res = await session.execute(attr_stmt)
            attr = attr_res.scalars().first()
            if attr:
                return LocalDatabaseNormalizer.normalize_attraction_as_place(attr)

            # Check Restaurant
            rest_stmt = select(Restaurant).where(Restaurant.id == val_uuid)
            rest_res = await session.execute(rest_stmt)
            rest = rest_res.scalars().first()
            if rest:
                return LocalDatabaseNormalizer.normalize_restaurant_as_place(rest)

        return None

    async def autocomplete_places(
        self,
        input_text: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 50000,
        **kwargs,
    ) -> List[TravelPlaceAutocompleteItem]:
        items: List[TravelPlaceAutocompleteItem] = []
        term = f"%{input_text.lower().strip()}%"

        async with self.session_factory() as session:
            # Destinations
            dest_stmt = select(Destination).where(func.lower(Destination.name).like(term)).limit(5)
            dest_res = await session.execute(dest_stmt)
            for d in dest_res.scalars().all():
                items.append(
                    TravelPlaceAutocompleteItem(
                        place_id=str(d.id),
                        primary_text=d.name,
                        secondary_text=f"{d.state}, India",
                        full_text=f"{d.name}, {d.state}, India",
                        types=["destination", d.region],
                        provider="local_db",
                    )
                )

            # Attractions
            attr_stmt = select(Attraction).where(func.lower(Attraction.name).like(term)).limit(5)
            attr_res = await session.execute(attr_stmt)
            for a in attr_res.scalars().all():
                items.append(
                    TravelPlaceAutocompleteItem(
                        place_id=str(a.id),
                        primary_text=a.name,
                        secondary_text=a.category,
                        full_text=f"{a.name} ({a.category})",
                        types=["attraction", a.category],
                        provider="local_db",
                    )
                )

        return items
