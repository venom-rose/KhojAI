import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy.types import UUID


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Default table name is pluralized lowercase of class name
        name = cls.__name__.lower()
        if name.endswith("y") and not name.endswith("ay") and not name.endswith("ey"):
            return f"{name[:-1]}ies"
        elif name.endswith("s"):
            return f"{name}es"
        return f"{name}s"


class UUIDPrimaryKeyMixin:
    """Mixin that adds a UUID primary key to models."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique identifier",
    )


class TimestampMixin:
    """Mixin that adds timezone-aware created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp of creation (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        doc="Timestamp of last update (UTC)",
    )


class SoftDeleteMixin:
    """Mixin that adds soft delete capabilities to models."""

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Flag indicating soft deletion",
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        doc="Timestamp of soft deletion (UTC)",
    )

    def soft_delete(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        self.is_deleted = False
        self.deleted_at = None
