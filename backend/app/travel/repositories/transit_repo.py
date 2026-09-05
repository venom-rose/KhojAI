"""Transit repository (Airport, TransportationOption, TravelRoute)."""

from typing import List, Optional, Sequence
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.travel.models.transit import Airport, TransportationOption, TravelRoute


class TransitRepository:
    """Data access operations for transit: Airports, TransportationOptions, TravelRoutes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Airports
    async def get_airport_by_id(self, airport_id: UUID) -> Optional[Airport]:
        stmt = select(Airport).options(selectinload(Airport.city)).where(Airport.id == airport_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_airport_by_iata(self, iata_code: str) -> Optional[Airport]:
        stmt = select(Airport).options(selectinload(Airport.city)).where(Airport.iata_code == iata_code.upper().strip())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_airports(self, limit: int = 50) -> Sequence[Airport]:
        stmt = select(Airport).order_by(Airport.name).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_or_create_airport(self, iata_code: str, name: str, **kwargs) -> Airport:
        airport = await self.get_airport_by_iata(iata_code)
        if not airport:
            airport = Airport(iata_code=iata_code.upper().strip(), name=name, **kwargs)
            self.session.add(airport)
            await self.session.flush()
        return airport

    # Transportation Options
    async def list_transportation_by_destination(self, destination_id: UUID) -> Sequence[TransportationOption]:
        stmt = (
            select(TransportationOption)
            .where(TransportationOption.destination_id == destination_id)
            .order_by(TransportationOption.duration_hours)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_transportation_option(self, **kwargs) -> TransportationOption:
        opt = TransportationOption(**kwargs)
        self.session.add(opt)
        await self.session.flush()
        return opt

    # Travel Routes
    async def list_routes_by_destination(self, destination_id: UUID) -> Sequence[TravelRoute]:
        stmt = (
            select(TravelRoute)
            .options(selectinload(TravelRoute.origin_city))
            .where(TravelRoute.destination_id == destination_id)
            .order_by(TravelRoute.typical_duration_hours)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_travel_route(self, **kwargs) -> TravelRoute:
        route = TravelRoute(**kwargs)
        self.session.add(route)
        await self.session.flush()
        return route
