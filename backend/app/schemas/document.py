import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

DocumentStatusType = Literal["uploaded", "processing", "ready", "failed"]
DocumentClassificationType = Literal["guide", "advisory", "field_note", "itinerary", "report", "other"]


class DocumentChunkOut(BaseModel):
    """Serialized document chunk representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    destination_id: Optional[uuid.UUID] = None
    chunk_index: int
    chunk_content: str
    token_count: Optional[int] = None
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class DocumentOut(BaseModel):
    """Summary representation of a document for library cards and lists."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: str
    source_url: Optional[str] = None
    document_type: str
    status: str
    error_message: Optional[str] = None
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    chunk_count: int = 0
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DocumentDetailOut(DocumentOut):
    """Detailed document representation with full content and chunks."""
    raw_content: str = ""
    chunks: List[DocumentChunkOut] = Field(default_factory=list)


class DocumentListOut(BaseModel):
    """Paginated collection of library documents."""
    items: List[DocumentOut]
    total: int
    limit: int
    offset: int


class DocumentSearchIn(BaseModel):
    """Semantic vector search inquiry across document knowledge base."""
    query: str = Field(..., min_length=1, max_length=2000, description="Search inquiry")
    top_k: int = Field(default=4, ge=1, le=20, description="Max number of matching chunks to retrieve")
    document_id: Optional[uuid.UUID] = Field(None, description="Scope search to a specific document")
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Similarity cutoff threshold")


class SearchResultChunkOut(BaseModel):
    """Matching chunk with computed cosine similarity score."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    content: str
    similarity: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentSearchOut(BaseModel):
    """Response containing retrieved semantic chunks."""
    query: str
    results: List[SearchResultChunkOut]
    count: int


class DocumentAskIn(BaseModel):
    """Ask a question grounded in the ingested document knowledge base (RAG)."""
    query: str = Field(..., min_length=1, max_length=2000, description="User question")
    document_id: Optional[uuid.UUID] = Field(None, description="Optional target document ID")
    top_k: int = Field(default=4, ge=1, le=10, description="Number of context chunks to inject")
    model: Optional[str] = Field(None, description="AI model to generate answer")
    stream: bool = Field(default=False, description="Stream answer via SSE")


class DocumentAskOut(BaseModel):
    """RAG-generated answer grounded on retrieved document context."""
    query: str
    answer: str
    model: str
    sources: List[SearchResultChunkOut]
    token_count: Optional[int] = None
