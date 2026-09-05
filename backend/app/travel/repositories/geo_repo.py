"""Geographic hierarchy repository (Country, State, City)."""

from typing import List, Optional, Sequence
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.travel.models.geo import City, Country, State


class GeoRepository:
    """Data access operations for countries, states, and cities."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Country
    async def get_country_by_id(self, country_id: UUID) -> Optional[Country]:
        stmt = select(Country).options(selectinload(Country.states)).where(Country.id == country_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_country_by_code(self, code: str) -> Optional[Country]:
        stmt = select(Country).options(selectinload(Country.states)).where(Country.code == code.upper())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_countries(self) -> Sequence[Country]:
        stmt = select(Country).order_by(Country.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_or_create_country(self, code: str, name: str, **kwargs) -> Country:
        country = await self.get_country_by_code(code)
        if not country:
            country = Country(code=code.upper(), name=name, **kwargs)
            self.session.add(country)
            await self.session.flush()
        return country

    # State
    async def get_state_by_id(self, state_id: UUID) -> Optional[State]:
        stmt = select(State).options(selectinload(State.cities)).where(State.id == state_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_states_by_country(self, country_id: UUID) -> Sequence[State]:
        stmt = select(State).where(State.country_id == country_id).order_by(State.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_state_by_name(self, country_id: UUID, name: str) -> Optional[State]:
        stmt = select(State).where(
            State.country_id == country_id,
            func.lower(State.name) == name.strip().lower(),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_or_create_state(self, country_id: UUID, name: str, region: str, code: Optional[str] = None, **kwargs) -> State:
        st = await self.get_state_by_name(country_id, name)
        if not st:
            st = State(country_id=country_id, name=name, region=region, code=code, **kwargs)
            self.session.add(st)
            await self.session.flush()
        return st

    # City
    async def get_city_by_id(self, city_id: UUID) -> Optional[City]:
        stmt = (
            select(City)
            .options(
                selectinload(City.state),
                selectinload(City.airports),
            )
            .where(City.id == city_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_cities_by_state(self, state_id: UUID) -> Sequence[City]:
        stmt = select(City).where(City.state_id == state_id).order_by(City.name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def search_cities(self, query: str, limit: int = 20) -> Sequence[City]:
        term = f"%{query.lower().strip()}%"
        stmt = (
            select(City)
            .where(
                or_(
                    func.lower(City.name).like(term),
                    func.lower(City.city_code).like(term),
                )
            )
            .order_by(City.name)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_or_create_city(
        self,
        state_id: UUID,
        name: str,
        city_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        elevation_meters: Optional[int] = None,
        **kwargs,
    ) -> City:
        stmt = select(City).where(
            City.state_id == state_id,
            func.lower(City.name) == name.strip().lower(),
        )
        result = await self.session.execute(stmt)
        city = result.scalars().first()
        if not city:
            city = City(
                state_id=state_id,
                name=name,
                city_code=city_code,
                latitude=latitude,
                longitude=longitude,
                elevation_meters=elevation_meters,
                **kwargs,
            )
            self.session.add(city)
            await self.session.flush()
        return city
