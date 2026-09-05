"""Points of Interest: Attractions, Activities, Hotels/Stays, and Restaurants/Eateries."""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from backend.app.database.base import (
    Base,
    ProvenanceMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Attraction(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Points of interest, natural landmarks, sacred architecture, and heritage sites."""

    __tablename__ = "attractions"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to parent destination",
    )

    city_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to nearest urban city/town",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        doc="Attraction name (e.g. 'Phugtal Monastery', 'Living Root Bridges', 'Hong Village')",
    )

    category: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        doc="Category keyword: 'Monastery', 'Waterfall', 'Sacred Grove', 'Viewpoint', 'Fort', 'Trek'",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Cultural, ecological, or historical narrative",
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

    entry_fee: Mapped[str] = mapped_column(
        String(50),
        default="Free",
        nullable=False,
        doc="Entry fee or community donation note",
    )

    timings: Mapped[str] = mapped_column(
        String(100),
        default="Sunrise to Sunset",
        nullable=False,
        doc="Standard visiting hours",
    )

    difficulty: Mapped[str] = mapped_column(
        String(30),
        default="Easy",
        nullable=False,
        doc="Physical difficulty tier: 'Easy', 'Moderate', 'Challenging', 'Strenuous'",
    )

    recommended_duration_mins: Mapped[int] = mapped_column(
        Integer,
        default=120,
        nullable=False,
        doc="Recommended time to experience in minutes",
    )

    tags: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Tags list (e.g. ['Heritage', 'Photography', 'Quiet'])",
    )

    # Relationships
    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="attractions",
    )

    city: Mapped[Optional["City"]] = relationship(
        "City",
        back_populates="attractions",
    )

    __table_args__ = (
        Index("idx_attractions_name_cat", "name", "category"),
        Index("idx_attractions_coordinates", "latitude", "longitude"),
        Index("idx_attractions_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Attraction name='{self.name}' category='{self.category}'>"


class Activity(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Experiential activities, guided walks, traditional workshops, and outdoor trails."""

    __tablename__ = "activities"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to parent destination",
    )

    city_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to nearest city",
    )

    title: Mapped[str] = mapped_column(
        String(200),
        index=True,
        nullable=False,
        doc="Activity title (e.g. 'Traditional Majuli Mask-Making Workshop', 'Paddy-Fish Cultivation Walk')",
    )

    activity_type: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        doc="Type: 'Cultural Workshop', 'Guided Trek', 'River Crossing', 'Birdwatching', 'Village Walk'",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Activity experience description",
    )

    duration_hours: Mapped[float] = mapped_column(
        Float,
        default=2.5,
        nullable=False,
        doc="Typical duration in hours",
    )

    price_range: Mapped[str] = mapped_column(
        String(50),
        default="₹300 – ₹800",
        nullable=False,
        doc="Cost range or honorarium per participant",
    )

    seasonality: Mapped[str] = mapped_column(
        String(100),
        default="All year",
        nullable=False,
        doc="Operational seasons (e.g. 'Oct – Mar', 'Monsoon harvest')",
    )

    guide_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether a local community guide is required",
    )

    # Relationships
    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="activities",
    )

    city: Mapped[Optional["City"]] = relationship(
        "City",
        back_populates="activities",
    )

    __table_args__ = (
        Index("idx_activities_title_type", "title", "activity_type"),
        Index("idx_activities_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Activity title='{self.title[:30]}' type='{self.activity_type}'>"


class Hotel(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Verified accommodation directory prioritizing community homestays, eco-lodges, and heritage retreats."""

    __tablename__ = "hotels"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to parent destination",
    )

    city_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to city",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        doc="Stay name (e.g. 'Donyi Hango Apatani Homestay', 'Tirthan Pine Eco-Cottage')",
    )

    stay_type: Mapped[str] = mapped_column(
        String(50),
        default="Homestay",
        nullable=False,
        index=True,
        doc="Accommodation category: 'Homestay', 'Eco-Lodge', 'Monastery Guesthouse', 'Heritage Haveli', 'Campsite'",
    )

    address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Physical or village location",
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

    price_per_night: Mapped[str] = mapped_column(
        String(100),
        default="₹1,500 – ₹2,500",
        nullable=False,
        doc="Estimated price per night including meals",
    )

    price_level: Mapped[str] = mapped_column(
        String(5),
        default="₹₹",
        nullable=False,
        doc="Price tier: '₹', '₹₹', '₹₹₹'",
    )

    rating: Mapped[Optional[float]] = mapped_column(
        Float,
        default=4.7,
        nullable=True,
        doc="Verified community quality rating (0.0 to 5.0)",
    )

    contact_phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Host contact or village council coordination number",
    )

    contact_email: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Reservation contact email",
    )

    booking_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Direct booking URL or community cooperative portal",
    )

    amenities: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="List of amenities (e.g. ['Hot water by wood fire', 'Home-cooked meals', 'Local guide'])",
    )

    sustainability_rating: Mapped[int] = mapped_column(
        Integer,
        default=90,
        nullable=False,
        doc="Eco-friendly and community revenue share index (0-100)",
    )

    # Relationships
    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="hotels",
    )

    city: Mapped[Optional["City"]] = relationship(
        "City",
        back_populates="hotels",
    )

    __table_args__ = (
        CheckConstraint("rating >= 0.0 AND rating <= 5.0", name="ck_hotels_rating"),
        Index("idx_hotels_name_type", "name", "stay_type"),
        Index("idx_hotels_coordinates", "latitude", "longitude"),
        Index("idx_hotels_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Hotel name='{self.name}' type='{self.stay_type}'>"


class Restaurant(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Indigenous food culture, tea stalls, dhabas, and traditional home kitchens."""

    __tablename__ = "restaurants"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to parent destination",
    )

    city_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to city",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        doc="Eatery name (e.g. 'Apatani Hearth Kitchen', 'Majuli Traditional Thali House')",
    )

    cuisine_type: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        doc="Cuisine style (e.g. 'Indigenous Tribal', 'Assamese Thali', 'Tibetan / Ladakhi', 'Pure Vegetarian')",
    )

    address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Location or market area",
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

    price_range: Mapped[str] = mapped_column(
        String(10),
        default="₹",
        nullable=False,
        doc="Relative cost tier: '₹' (Budget dhaba), '₹₹' (Family dining), '₹₹₹' (Specialty)",
    )

    rating: Mapped[Optional[float]] = mapped_column(
        Float,
        default=4.5,
        nullable=True,
        doc="Quality rating (0.0 to 5.0)",
    )

    must_try_dishes: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Recommended local specialties (e.g. ['Piku bamboo shoot', 'Apong millet brew', 'Thukpa'])",
    )

    opening_hours: Mapped[str] = mapped_column(
        String(100),
        default="11:00 AM – 8:30 PM",
        nullable=False,
        doc="Operational hours",
    )

    # Relationships
    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="restaurants",
    )

    city: Mapped[Optional["City"]] = relationship(
        "City",
        back_populates="restaurants",
    )

    __table_args__ = (
        CheckConstraint("rating >= 0.0 AND rating <= 5.0", name="ck_restaurants_rating"),
        Index("idx_restaurants_name_cuisine", "name", "cuisine_type"),
        Index("idx_restaurants_coordinates", "latitude", "longitude"),
        Index("idx_restaurants_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Restaurant name='{self.name}' cuisine='{self.cuisine_type}'>"
