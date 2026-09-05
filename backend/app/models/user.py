import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UUID
from backend.app.database.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """User account entity for travelers, contributors, and administrators."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="Unique user email address",
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Bcrypt or Argon2 hashed password",
    )

    full_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        doc="User full or display name",
    )

    role: Mapped[str] = mapped_column(
        String(50),
        default="user",
        nullable=False,
        index=True,
        doc="Access control role: user, moderator, admin",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Flag indicating active account status",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Email verification status",
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Profile avatar image URL",
    )

    bio: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Short traveler biography or note",
    )

    theme_preference: Mapped[str] = mapped_column(
        String(20),
        default="light",
        nullable=False,
        doc="UI theme preference: light, dark, system",
    )

    travel_preferences: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
        doc="Default travel preferences (budget, style, days, interests, group)",
    )

    # Relationships
    sessions: Mapped[List["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    itineraries: Mapped[List["Itinerary"]] = relationship(
        "Itinerary",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    contributions: Mapped[List["Contribution"]] = relationship(
        "Contribution",
        back_populates="user",
    )

    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


class Session(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistent user session supporting refresh token rotation and revocation."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the authenticated user",
    )

    session_token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        doc="Opaque cryptographically random refresh/session token",
    )

    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Client user agent string",
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="Client IP address",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Session expiration timestamp (UTC)",
    )

    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Revocation status flag",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
    )

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= exp

    @property
    def is_valid(self) -> bool:
        return not self.is_revoked and not self.is_expired

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id} revoked={self.is_revoked}>"
