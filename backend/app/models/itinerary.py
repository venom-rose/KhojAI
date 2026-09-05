import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import CheckConstraint, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from backend.app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Itinerary(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """AI-generated or curated travel itinerary matching the planner results contract."""

    __tablename__ = "itineraries"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key if itinerary is claimed/saved by an authenticated user",
    )

    share_token: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        doc="URL-safe share token (e.g. 'ziro-5d-a8b2')",
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Headline itinerary title (e.g. 'A slower side of the Northeast')",
    )

    subtitle: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Subtitle tag (e.g. 'Slow travel · 5 days · 2 people')",
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Executive narrative summary of the journey",
    )

    total_budget: Mapped[str] = mapped_column(
        String(100),
        default="₹15,000 / person",
        nullable=False,
        doc="Estimated budget string",
    )

    preferences: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Raw planner preferences JSON: budget, days, style, interests, group",
    )

    primary_destination_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Primary destination featured in this itinerary",
    )

    match_score: Mapped[int] = mapped_column(
        Integer,
        default=90,
        nullable=False,
        doc="Overall match percentage (0-100)",
    )

    rationale_bullets: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
        doc="Explainability rationale bullet points justifying the recommendation",
    )

    __table_args__ = (
        CheckConstraint("match_score >= 0 AND match_score <= 100", name="ck_itinerary_match_score"),
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="itineraries",
    )

    primary_destination: Mapped[Optional["Destination"]] = relationship(
        "Destination",
        back_populates="itineraries",
    )

    days: Mapped[List["ItineraryDay"]] = relationship(
        "ItineraryDay",
        back_populates="itinerary",
        cascade="all, delete-orphan",
        order_by="ItineraryDay.sort_order",
    )

    def __repr__(self) -> str:
        return f"<Itinerary id={self.id} token={self.share_token} title='{self.title[:30]}'>"


class ItineraryDay(Base, UUIDPrimaryKeyMixin):
    """Day-by-day sequenced route stop in an itinerary."""

    __tablename__ = "itinerary_days"

    itinerary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("itineraries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the parent itinerary",
    )

    day_number: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Formatted day label (e.g. '01', '02')",
    )

    place_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Location name for the day",
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Editorial day title (e.g. 'Arrive into the green')",
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Descriptive narrative of activities and pacing",
    )

    accent_color: Mapped[str] = mapped_column(
        String(20),
        default="#5d6b43",
        nullable=False,
        doc="Hex accent color token for timeline rendering",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Numerical sorting order",
    )

    itinerary: Mapped["Itinerary"] = relationship(
        "Itinerary",
        back_populates="days",
    )

    def __repr__(self) -> str:
        return f"<ItineraryDay itinerary_id={self.itinerary_id} day={self.day_number} place='{self.place_name}'>"
