import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


ChatMessageSenderType = Literal["user", "assistant", "system"]


class AttachmentItem(BaseModel):
    """Attachment metadata for images, travel guides, or route maps."""
    type: str = Field(default="image", description="Attachment type, e.g., 'image', 'document', 'url'")
    url: str = Field(..., description="Direct link or resource URL")
    name: Optional[str] = Field(None, description="Display name or filename")
    size: Optional[int] = Field(None, description="Size in bytes if applicable")


class MessageCreateIn(BaseModel):
    """Payload for submitting a user message to a conversation."""
    content: str = Field(..., min_length=1, max_length=20000, description="Text content of the message")
    sender_type: ChatMessageSenderType = Field(default="user", description="Message sender type")
    model: Optional[str] = Field(None, description="Optional override for AI model to use")
    stream: bool = Field(default=False, description="Whether to stream response tokens via SSE")
    attachments: Optional[List[AttachmentItem]] = Field(default=None, description="Optional attached files or media")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary custom metadata or client signals")


class MessageRegenerateIn(BaseModel):
    """Payload for regenerating an assistant response."""
    model: Optional[str] = Field(None, description="Optional override for AI model to use")
    stream: bool = Field(default=False, description="Whether to stream regenerated response tokens via SSE")


class ChatMessageOut(BaseModel):
    """Serialized message representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_type: str
    content: str
    model_name: Optional[str] = None
    token_count: Optional[int] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ConversationCreateIn(BaseModel):
    """Payload to initiate a new chat conversation."""
    title: Optional[str] = Field(None, max_length=255, description="Conversation title or travel focus")
    model: Optional[str] = Field(None, max_length=100, description="Preferred AI model for conversation")
    initial_message: Optional[str] = Field(None, max_length=20000, description="Optional first user message")


class ConversationUpdateIn(BaseModel):
    """Payload for editing a conversation's title or pin/archive state."""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="Updated conversation title")
    is_pinned: Optional[bool] = Field(None, description="Pin conversation to top")
    is_archived: Optional[bool] = Field(None, description="Archive conversation")


class ConversationOut(BaseModel):
    """Summary representation of a conversation for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: str
    summary: Optional[str] = None
    model: Optional[str] = None
    is_pinned: bool
    is_archived: bool
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationDetailOut(ConversationOut):
    """Detailed conversation representation including chronological message history."""
    messages: List[ChatMessageOut] = Field(default_factory=list)


class ConversationListOut(BaseModel):
    """Paginated collection of conversations."""
    items: List[ConversationOut]
    total: int
    limit: int
    offset: int


class ChatStreamChunk(BaseModel):
    """Data payload for Server-Sent Events (SSE) streaming."""
    token: str = ""
    done: bool = False
    message_id: Optional[str] = None
    finish_reason: Optional[str] = None
    error: Optional[str] = None
