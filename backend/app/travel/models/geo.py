"""Geographic hierarchy entities: Country, State/Province, and City."""

import uuid
from typing import List, Optional
from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from backend.app.database.base import (
    Base,
    ProvenanceMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Country(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Sovereign nation entity."""

    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(
        String(2),
        unique=True,
        index=True,
        nullable=False,
        doc="ISO 3166-1 alpha-2 code (e.g. 'IN')",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        doc="Common English country name",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR",
        nullable=False,
        doc="ISO 4217 currency code (e.g. 'INR')",
    )

    phone_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        default="+91",
        nullable=True,
        doc="International calling prefix",
    )

    continent: Mapped[str] = mapped_column(
        String(50),
        default="Asia",
        nullable=False,
        doc="Continent name",
    )

    # Relationships
    states: Mapped[List["State"]] = relationship(
        "State",
        back_populates="country",
        cascade="all, delete-orphan",
    )

    destinations: Mapped[List["Destination"]] = relationship(
        "Destination",
        back_populates="country",
    )

    __table_args__ = (
        Index("idx_countries_code_name", "code", "name"),
        Index("idx_countries_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Country code={self.code} name='{self.name}'>"


class State(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Sub-national administrative division (State or Union Territory)."""

    __tablename__ = "states"

    country_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("countries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to parent country",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        doc="State or territory name (e.g. 'Arunachal Pradesh', 'Himachal Pradesh')",
    )

    code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        index=True,
        doc="Regional ISO or state code (e.g. 'AR', 'HP')",
    )

    region: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        doc="Geographic region (e.g. 'Northeast', 'Himalayas', 'South')",
    )

    # Relationships
    country: Mapped["Country"] = relationship(
        "Country",
        back_populates="states",
    )

    cities: Mapped[List["City"]] = relationship(
        "City",
        back_populates="state",
        cascade="all, delete-orphan",
    )

    destinations: Mapped[List["Destination"]] = relationship(
        "Destination",
        back_populates="state_rel",
    )

    __table_args__ = (
        Index("idx_states_name_region", "name", "region"),
        Index("idx_states_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<State name='{self.name}' region='{self.region}'>"


class City(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """City, town, or transit gateway urban hub."""

    __tablename__ = "cities"

    state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("states.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to parent state",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        doc="City name (e.g. 'Naharlagun', 'Itanagar', 'Kullu', 'Leh')",
    )

    city_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        index=True,
        doc="Standard city or municipality code",
    )

    latitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="WGS84 latitude coordinate",
    )

    longitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="WGS84 longitude coordinate",
    )

    elevation_meters: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Elevation above sea level in meters",
    )

    # Relationships
    state: Mapped["State"] = relationship(
        "State",
        back_populates="cities",
    )

    destinations: Mapped[List["Destination"]] = relationship(
        "Destination",
        back_populates="city",
    )

    attractions: Mapped[List["Attraction"]] = relationship(
        "Attraction",
        back_populates="city",
    )

    activities: Mapped[List["Activity"]] = relationship(
        "Activity",
        back_populates="city",
    )

    hotels: Mapped[List["Hotel"]] = relationship(
        "Hotel",
        back_populates="city",
    )

    restaurants: Mapped[List["Restaurant"]] = relationship(
        "Restaurant",
        back_populates="city",
    )

    airports: Mapped[List["Airport"]] = relationship(
        "Airport",
        back_populates="city",
    )

    travel_routes_originated: Mapped[List["TravelRoute"]] = relationship(
        "TravelRoute",
        back_populates="origin_city",
    )

    __table_args__ = (
        Index("idx_cities_name", "name"),
        Index("idx_cities_coordinates", "latitude", "longitude"),
        Index("idx_cities_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<City name='{self.name}'>"
