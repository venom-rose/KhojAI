import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, UUID
from backend.app.database.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from backend.app.models.destination import Destination
    from backend.app.models.user import User


class Document(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Knowledge base documents (travel advisories, verified regional guides, uploaded notes)."""

    __tablename__ = "documents"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Owner user ID (null for system knowledge base)",
    )

    title: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
        doc="Title of the source document or advisory",
    )

    source_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Reference URL or citation source",
    )

    document_type: Mapped[str] = mapped_column(
        String(50),
        default="guide",
        nullable=False,
        index=True,
        doc="Type classification: 'guide', 'advisory', 'field_note', 'itinerary', 'report'",
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False,
        index=True,
        doc="Processing state: 'uploaded', 'processing', 'ready', 'failed'",
    )

    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed error message if processing fails",
    )

    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Safe path to uploaded physical file on disk (outside executable paths)",
    )

    original_filename: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Sanitized original filename as uploaded by the user",
    )

    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="File size in bytes",
    )

    mime_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Detected MIME content type",
    )

    raw_content: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
        doc="Extracted and cleaned raw text content of the document",
    )

    metadata_json: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Extensible metadata: chunk_count, word_count, language, travel_tags",
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="documents",
    )

    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DocumentChunk.chunk_index.asc()",
    )

    @property
    def chunk_count(self) -> int:
        if self.metadata_json and "chunk_count" in self.metadata_json:
            return int(self.metadata_json["chunk_count"])
        try:
            return len(self.chunks) if self.chunks else 0
        except Exception:
            return 0

    def __repr__(self) -> str:
        return f"<Document id={self.id} title='{self.title[:30]}' status='{self.status}'>"


class DocumentChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Semantic chunk with vector embeddings for RAG retrieval."""

    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent document foreign key",
    )

    destination_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("destinations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Associated destination foreign key",
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Zero-based sequence order of the chunk in document",
    )

    chunk_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Segmented text block used as context injection",
    )

    token_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Estimated token count of this chunk",
    )

    embedding: Mapped[Optional[List[float]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        doc="Vector embedding array (e.g. 256, 768 or 1536 floats)",
    )

    chunk_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        default=dict,
        nullable=False,
        doc="Context metadata: topic, season, route, page_number, word_count",
    )

    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

    destination: Mapped[Optional["Destination"]] = relationship(
        "Destination",
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc_id={self.document_id} index={self.chunk_index}>"
