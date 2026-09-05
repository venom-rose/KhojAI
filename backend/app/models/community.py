import uuid
from typing import Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from backend.app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class CommunityStory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Curated community perspective quotes displayed on /community."""

    __tablename__ = "community_stories"

    destination_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to associated destination",
    )

    author_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Attributed author name (e.g. 'Ananya R.')",
    )

    author_role: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        doc="Author context or title (e.g. 'Local guide · Ziro')",
    )

    initials: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Avatar initials badge text (e.g. 'AR')",
    )

    quote: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Editorial quote text",
    )

    tag: Mapped[str] = mapped_column(
        String(100),
        default="Local perspective",
        nullable=False,
        doc="Category pill label (e.g. 'Recent stay', 'Trust note')",
    )

    time_display: Mapped[str] = mapped_column(
        String(50),
        default="Recently",
        nullable=False,
        doc="Relative timestamp display string (e.g. '2 days ago')",
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Display sort order on community page",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Visibility toggle",
    )

    destination: Mapped[Optional["Destination"]] = relationship(
        "Destination",
        back_populates="stories",
    )

    def __repr__(self) -> str:
        return f"<CommunityStory id={self.id} author='{self.author_name}'>"
