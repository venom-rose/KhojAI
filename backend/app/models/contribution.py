import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from backend.app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Contribution(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Community-contributed field notes and local insights from travellers."""

    __tablename__ = "contributions"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key if contributor was authenticated",
    )

    destination_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key if linked to an existing destination record",
    )

    place_name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
        doc="Name of the village, viewpoint, trail, or establishment",
    )

    contributor_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        doc="Name or alias for attribution",
    )

    story_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="First-hand experiential field note and tips",
    )

    photo_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Path or URL to an uploaded traveler photo",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
        index=True,
        doc="Moderation status: 'pending', 'approved', 'rejected'",
    )

    moderation_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Internal notes from content reviewer",
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of moderation approval or rejection",
    )

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')", name="ck_contribution_status"),
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="contributions",
    )

    destination: Mapped[Optional["Destination"]] = relationship(
        "Destination",
        back_populates="contributions",
    )

    def __repr__(self) -> str:
        return f"<Contribution id={self.id} place='{self.place_name}' status={self.status}>"
