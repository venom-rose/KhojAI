import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DestinationSearchResultItem(BaseModel):
    """Ranked destination search result."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    state: str
    region: str
    category: str
    best_season: str
    budget: str
    trust_score: int
    description: str
    image_url: str
    accent_color: str = "#5d6b43"
    tags: List[str] = Field(default_factory=list)
    relevance_score: float = 1.0


class DocumentSearchResultItem(BaseModel):
    """Ranked document chunk search result with vector similarity."""
    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    document_type: str
    content: str
    similarity: float
    relevance_score: float
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSearchResultItem(BaseModel):
    """Ranked conversation inquiry search result."""
    model_config = ConfigDict(from_attributes=True)

    conversation_id: uuid.UUID
    title: str
    summary: Optional[str] = None
    model: Optional[str] = None
    matched_message: Optional[str] = None
    is_pinned: bool = False
    is_archived: bool = False
    relevance_score: float = 1.0
    updated_at: datetime


class GlobalSearchOut(BaseModel):
    """Omnisearch collection across destinations, documents, and conversations."""
    query: str
    destinations: List[DestinationSearchResultItem] = Field(default_factory=list)
    documents: List[DocumentSearchResultItem] = Field(default_factory=list)
    conversations: List[ConversationSearchResultItem] = Field(default_factory=list)
    total_hits: int = 0


class PaginatedDestinationSearchOut(BaseModel):
    """Paginated collection of filtered destinations."""
    items: List[DestinationSearchResultItem]
    total: int
    limit: int
    offset: int


class PaginatedDocumentSearchOut(BaseModel):
    """Paginated collection of searched documents and chunks."""
    items: List[DocumentSearchResultItem]
    total: int
    limit: int
    offset: int


class PaginatedConversationSearchOut(BaseModel):
    """Paginated collection of searched conversations."""
    items: List[ConversationSearchResultItem]
    total: int
    limit: int
    offset: int
