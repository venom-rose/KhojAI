"""Transit connectivity entities: Airports, Transportation Options, and Route Corridors."""

import uuid
from typing import Optional
from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from backend.app.database.base import (
    Base,
    ProvenanceMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Airport(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Aviation gateways, domestic airstrips, and regional helicopter pads."""

    __tablename__ = "airports"

    city_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="City or metropolitan gateway served by this airport",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        doc="Airport name (e.g. 'Donyi Polo Airport, Hollongi', 'Kushok Bakula Rimpochee Airport')",
    )

    iata_code: Mapped[str] = mapped_column(
        String(3),
        unique=True,
        index=True,
        nullable=False,
        doc="3-letter IATA code (e.g. 'HGI', 'IXL', 'GAU')",
    )

    icao_code: Mapped[Optional[str]] = mapped_column(
        String(4),
        nullable=True,
        doc="4-letter ICAO code",
    )

    latitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="WGS84 latitude",
    )

    longitude: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="WGS84 longitude",
    )

    is_international: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the airport operates international flights",
    )

    # Relationships
    city: Mapped[Optional["City"]] = relationship(
        "City",
        back_populates="airports",
    )

    __table_args__ = (
        Index("idx_airports_iata", "iata_code"),
        Index("idx_airports_coordinates", "latitude", "longitude"),
        Index("idx_airports_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Airport code={self.iata_code} name='{self.name}'>"


class TransportationOption(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """First/last mile transit connections: shared taxis, state transport buses, ferries, and private cabs."""

    __tablename__ = "transportation_options"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to target destination",
    )

    transport_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        doc="Transit mode: 'Shared Sumo Taxi', 'State Transport Bus', 'Private Cab', 'River Ferry', 'Mountain Rail'",
    )

    origin_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Hub of origin (e.g. 'Naharlagun Railway Station', 'Jorhat Nimati Ghat', 'Dehradun')",
    )

    destination_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Final arrival point (e.g. 'Hapoli / Ziro Old Town', 'Kamalabari Ghat, Majuli')",
    )

    duration_hours: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Estimated transit duration in hours",
    )

    cost_estimate: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Cost range per seat or vehicle (e.g. '₹350 / seat', '₹3,500 full cab')",
    )

    frequency: Mapped[str] = mapped_column(
        String(100),
        default="Daily",
        nullable=False,
        doc="Service frequency (e.g. 'Departures between 6:00 AM and 8:00 AM only', 'Hourly')",
    )

    operator_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        doc="Operator or syndicate name (e.g. 'Arunachal Pradesh State Transport Services')",
    )

    booking_tips: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Practical booking advice (e.g. 'Reserve Sumo seat 1 day in advance at town counter')",
    )

    # Relationships
    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="transportation_options",
    )

    __table_args__ = (
        Index("idx_transport_dest_type", "destination_id", "transport_type"),
        Index("idx_transport_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<TransportationOption type='{self.transport_type}' {self.origin_name} -> {self.destination_name}>"


class TravelRoute(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Curated route corridors with distance, road conditions, and scenic indices."""

    __tablename__ = "travel_routes"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to target destination",
    )

    origin_city_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to departure gateway city",
    )

    route_name: Mapped[str] = mapped_column(
        String(200),
        index=True,
        nullable=False,
        doc="Route corridor title (e.g. 'Guwahati to Ziro via NH15 & Potin', 'Jorhat to Majuli via River Ferry')",
    )

    mode: Mapped[str] = mapped_column(
        String(50),
        default="Road",
        nullable=False,
        doc="Primary travel mode: 'Road', 'Train + Road', 'Road + Ferry', 'Trek'",
    )

    distance_km: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Total distance in kilometers",
    )

    typical_duration_hours: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Realistic driving or transfer time in hours",
    )

    road_condition: Mapped[str] = mapped_column(
        String(100),
        default="Metalled two-lane highway with mountain curves",
        nullable=False,
        doc="Road surface and difficulty description",
    )

    scenic_rating: Mapped[int] = mapped_column(
        Integer,
        default=9,
        nullable=False,
        doc="Scenic index between 1 and 10",
    )

    seasonal_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Weather-dependent routing advice (e.g. 'Heavy monsoon fog from July to August')",
    )

    # Relationships
    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="travel_routes",
    )

    origin_city: Mapped[Optional["City"]] = relationship(
        "City",
        back_populates="travel_routes_originated",
    )

    __table_args__ = (
        CheckConstraint("scenic_rating >= 1 AND scenic_rating <= 10", name="ck_routes_scenic_rating"),
        Index("idx_routes_dest_mode", "destination_id", "mode"),
        Index("idx_routes_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<TravelRoute name='{self.route_name}' dist={self.distance_km}km>"
