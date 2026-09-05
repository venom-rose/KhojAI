import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from backend.app.database.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Destination(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Destination entity representing a verified, lesser-known Indian location."""

    __tablename__ = "destinations"

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        doc="URL-friendly unique slug identifier (e.g. 'ziro', 'tirthan-valley')",
    )

    name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        doc="Official destination name",
    )

    state: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        doc="Indian state or union territory",
    )

    region: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        doc="Geographic region (e.g. 'Himalayas', 'Northeast', 'South')",
    )

    category: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Category keywords (e.g. 'Nature · Culture', 'River · Culture')",
    )

    best_season: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Optimal visiting months (e.g. 'Oct – Nov', 'Mar – Jun')",
    )

    budget: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Relative cost tier: '₹', '₹₹', or '₹₹₹'",
    )

    trust_score: Mapped[int] = mapped_column(
        Integer,
        default=85,
        nullable=False,
        doc="Calculated aggregate trust score between 0 and 100",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Rich editorial narrative describing the destination's sense of place",
    )

    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Path or URL to primary landscape image",
    )

    accent_color: Mapped[str] = mapped_column(
        String(20),
        default="#5d6b43",
        nullable=False,
        doc="Hex color token for UI cards and theme accenting",
    )

    coordinate_x: Mapped[str] = mapped_column(
        String(20),
        default="50%",
        nullable=False,
        doc="Percentage X coordinate for the map visualization (e.g. '71%')",
    )

    coordinate_y: Mapped[str] = mapped_column(
        String(20),
        default="50%",
        nullable=False,
        doc="Percentage Y coordinate for the map visualization (e.g. '24%')",
    )

    demo_note: Mapped[str] = mapped_column(
        Text,
        default="Illustrative demo content for review; not a live travel advisory.",
        nullable=False,
        doc="Traveler advisory or prototype caveat note",
    )

    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Visibility toggle for published destinations",
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Flag indicating landing page featured status",
    )

    # Database-level Constraints
    __table_args__ = (
        CheckConstraint("trust_score >= 0 AND trust_score <= 100", name="ck_destinations_trust_score"),
        CheckConstraint("length(budget) >= 1 AND length(budget) <= 5", name="ck_destinations_budget"),
        Index("idx_destinations_filter", "region", "budget", "state"),
    )

    # Relationships
    trust_metric: Mapped[Optional["TrustMetric"]] = relationship(
        "TrustMetric",
        back_populates="destination",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    tags: Mapped[List["DestinationTag"]] = relationship(
        "DestinationTag",
        back_populates="destination",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    stories: Mapped[List["CommunityStory"]] = relationship(
        "CommunityStory",
        back_populates="destination",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    contributions: Mapped[List["Contribution"]] = relationship(
        "Contribution",
        back_populates="destination",
    )

    itineraries: Mapped[List["Itinerary"]] = relationship(
        "Itinerary",
        back_populates="primary_destination",
    )

    def __repr__(self) -> str:
        return f"<Destination id={self.id} slug={self.slug} score={self.trust_score}>"


class DestinationTag(Base, UUIDPrimaryKeyMixin):
    """Normalized tags associated with a destination (e.g. 'Slow travel', 'Rice terraces')."""

    __tablename__ = "destination_tags"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the parent destination",
    )

    tag: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
        doc="Tag keyword",
    )

    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="tags",
    )

    def __repr__(self) -> str:
        return f"<DestinationTag destination_id={self.destination_id} tag={self.tag}>"


class TrustMetric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Destination Intelligence metrics measuring information quality and confidence."""

    __tablename__ = "trust_metrics"

    destination_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        doc="Foreign key to destination (1:1 relationship)",
    )

    source_quality: Mapped[int] = mapped_column(
        Integer,
        default=85,
        nullable=False,
        doc="Source reliability and authority score (0-100)",
    )

    recency: Mapped[int] = mapped_column(
        Integer,
        default=85,
        nullable=False,
        doc="Information freshness score (0-100)",
    )

    community_agreement: Mapped[int] = mapped_column(
        Integer,
        default=85,
        nullable=False,
        doc="Consensus score across multiple independent travelers (0-100)",
    )

    completeness: Mapped[int] = mapped_column(
        Integer,
        default=85,
        nullable=False,
        doc="Coverage score across route, stay, food, and safety (0-100)",
    )

    last_audited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Timestamp of the most recent intelligence audit (UTC)",
    )

    __table_args__ = (
        CheckConstraint("source_quality >= 0 AND source_quality <= 100", name="ck_trust_source_quality"),
        CheckConstraint("recency >= 0 AND recency <= 100", name="ck_trust_recency"),
        CheckConstraint("community_agreement >= 0 AND community_agreement <= 100", name="ck_trust_community_agreement"),
        CheckConstraint("completeness >= 0 AND completeness <= 100", name="ck_trust_completeness"),
    )

    destination: Mapped["Destination"] = relationship(
        "Destination",
        back_populates="trust_metric",
    )

    def __repr__(self) -> str:
        return f"<TrustMetric destination_id={self.destination_id} avg={(self.source_quality + self.recency + self.community_agreement + self.completeness) // 4}>"
