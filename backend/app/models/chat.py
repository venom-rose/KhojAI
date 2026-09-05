import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, UUID

from backend.app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.models.user import User


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Conversation entity grouping a thread of messages between a user and KhojAI assistant."""

    __tablename__ = "conversations"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Owner user ID, or null for anonymous/guest sessions",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Conversation",
        doc="Conversation title or travel inquiry headline",
    )

    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Short LLM-generated or computed summary of discussion",
    )

    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Preferred AI model identifier for this conversation",
    )

    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether conversation is pinned to the top of the list",
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Whether conversation has been archived",
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="conversations",
    )

    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessage.created_at.asc()",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} title='{self.title}' user_id={self.user_id}>"


class ChatMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Individual message within a conversation."""

    __tablename__ = "chat_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent conversation ID",
    )

    sender_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Sender type: 'user', 'assistant', or 'system'",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Raw text or markdown content of message",
    )

    model_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="AI model name used to generate this response",
    )

    token_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Estimated or actual token count",
    )

    metadata_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Extensible metadata: attachments, citations, itinerary links, travel cards",
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} conversation_id={self.conversation_id} sender={self.sender_type}>"
