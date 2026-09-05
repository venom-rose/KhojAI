"""Destination classification, seasonal climate profiles, and travel tips."""

import uuid
from typing import List, Optional
from sqlalchemy import Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from backend.app.database.base import (
    Base,
    ProvenanceMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class DestinationCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Destination categorization taxonomy (e.g. 'High-Altitude Valley', 'Living Root Bridges', 'River Island')."""

    __tablename__ = "destination_categories"

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique category slug (e.g. 'high-altitude-valley', 'river-island')",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Human-readable category name",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Category description and distinctive travel traits",
    )

    icon_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        default="Compass",
        nullable=True,
        doc="Lucide icon identifier for UI rendering",
    )

    # Relationships
    destinations: Mapped[List["Destination"]] = relationship(
        "Destination",
        back_populates="category_entity",
    )

    __table_args__ = (
        Index("idx_dest_categories_slug_name", "slug", "name"),
        Index("idx_dest_categories_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<DestinationCategory slug='{self.slug}' name='{self.name}'>"


class Season(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Seasonal climate, weather conditions, and travel advisories per destination."""

    __tablename__ = "seasons"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to target destination",
    )

    season_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Season identifier (e.g. 'Autumn', 'Winter', 'Monsoon', 'Spring', 'Summer')",
    )

    start_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Calendar start month (1-12)",
    )

    end_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Calendar end month (1-12)",
    )

    weather_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Narrative summary of weather, cloud cover, and trail conditions",
    )

    avg_temp_min_c: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Average low temperature in Celsius",
    )

    avg_temp_max_c: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Average high temperature in Celsius",
    )

    rainfall_level: Mapped[str] = mapped_column(
        String(20),
        default="moderate",
        nullable=False,
        doc="Rainfall intensity indicator: 'dry', 'low', 'moderate', 'heavy', 'torrential'",
    )

    is_recommended: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this season is recommended for standard exploration",
    )

    advisory_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Seasonal caveats (e.g. 'Pack thermal base layers', 'Landslide risk on mountain passes')",
    )

    # Relationships
    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="seasons",
    )

    __table_args__ = (
        CheckConstraint("start_month >= 1 AND start_month <= 12", name="ck_seasons_start_month"),
        CheckConstraint("end_month >= 1 AND end_month <= 12", name="ck_seasons_end_month"),
        Index("idx_seasons_dest_rec", "destination_id", "is_recommended"),
        Index("idx_seasons_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<Season destination_id={self.destination_id} season='{self.season_name}'>"


class TravelTip(Base, UUIDPrimaryKeyMixin, TimestampMixin, ProvenanceMixin):
    """Actionable logistics, cultural etiquette, packing, and safety tips."""

    __tablename__ = "travel_tips"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to target destination",
    )

    category: Mapped[str] = mapped_column(
        String(50),
        default="logistics",
        nullable=False,
        doc="Tip category: 'logistics', 'etiquette', 'packing', 'connectivity', 'safety', 'food'",
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Tip headline or rule",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Comprehensive tip details and context",
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Priority sorting order (1=Crucial, 2=Important, 3=Helpful)",
    )

    # Relationships
    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="travel_tips",
    )

    __table_args__ = (
        Index("idx_tips_dest_cat", "destination_id", "category"),
        Index("idx_tips_provenance", "source", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<TravelTip destination_id={self.destination_id} title='{self.title[:30]}'>"
