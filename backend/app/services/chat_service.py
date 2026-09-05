import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.ai.base import BaseAIProvider
from backend.app.ai.factory import get_ai_provider
from backend.app.models.chat import ChatMessage, Conversation
from backend.app.schemas.chat import (
    AttachmentItem,
    ChatMessageOut,
    ConversationCreateIn,
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    ConversationUpdateIn,
    MessageCreateIn,
)

logger = logging.getLogger(__name__)

KHOJAI_SYSTEM_PROMPT = (
    "You are KHOJAI (Hidden India AI), an intelligent travel guide and field companion. "
    "You specialize in uncovered, authentic, and culturally rich journeys across India. "
    "Your recommendations prioritize unhurried pacing, seasonal timing, community stewardship, "
    "and quiet landscapes over commercial tourist circuits. Be concise, insightful, and practical."
)


class ChatService:
    """Service orchestrating chat conversations, message persistence, and AI response generation."""

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self._provider = provider

    @property
    def provider(self) -> BaseAIProvider:
        if self._provider is None:
            self._provider = get_ai_provider()
        return self._provider

    async def get_conversation_or_404(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        load_messages: bool = False,
    ) -> Conversation:
        """Fetch conversation by ID, checking user ownership."""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        if load_messages:
            stmt = stmt.options(selectinload(Conversation.messages))

        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation with ID '{conversation_id}' not found.",
            )

        # Enforce strict user isolation: if conversation belongs to a user, unauthorized users cannot access it
        if conversation.user_id is not None:
            if user_id is None or conversation.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to access this conversation.",
                )

        return conversation

    async def create_conversation(
        self,
        db: AsyncSession,
        data: ConversationCreateIn,
        user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[Conversation, Optional[ChatMessage], Optional[ChatMessage]]:
        """Create a new conversation, with optional initial message and AI reply."""
        title = data.title or "New Conversation"
        conversation = Conversation(
            user_id=user_id,
            title=title,
            model=data.model,
        )
        db.add(conversation)
        await db.flush()

        user_msg = None
        assistant_msg = None

        if data.initial_message:
            # Auto-title conversation if default
            if title == "New Conversation":
                conversation.title = data.initial_message[:50].strip() + ("..." if len(data.initial_message) > 50 else "")

            # Persist initial user message
            user_msg = ChatMessage(
                conversation_id=conversation.id,
                sender_type="user",
                content=data.initial_message,
                model_name=data.model,
            )
            db.add(user_msg)
            await db.flush()

            # Generate initial AI reply
            messages_payload = [{"role": "user", "content": data.initial_message}]
            ai_res = await self.provider.generate_response(
                messages=messages_payload,
                system_prompt=KHOJAI_SYSTEM_PROMPT,
                model=data.model,
            )

            assistant_msg = ChatMessage(
                conversation_id=conversation.id,
                sender_type="assistant",
                content=ai_res.content,
                model_name=ai_res.model_name,
                token_count=ai_res.token_count,
                metadata_json=ai_res.metadata,
            )
            db.add(assistant_msg)
            conversation.updated_at = datetime.now(timezone.utc)
            await db.flush()

        await db.commit()
        await db.refresh(conversation)
        return conversation, user_msg, assistant_msg

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
        include_archived: bool = False,
    ) -> ConversationListOut:
        """Retrieve paginated conversations strictly isolated to the user."""
        conditions = []
        if user_id is not None:
            conditions.append(Conversation.user_id == user_id)
        else:
            # Unauthenticated callers can only see unassigned/anonymous sessions
            conditions.append(Conversation.user_id.is_(None))
        if not include_archived:
            conditions.append(Conversation.is_archived.is_(False))
        if search:
            conditions.append(Conversation.title.ilike(f"%{search}%"))

        # Message count subquery
        msg_count_sub = (
            select(
                ChatMessage.conversation_id,
                func.count(ChatMessage.id).label("msg_count"),
            )
            .group_by(ChatMessage.conversation_id)
            .subquery()
        )

        query = (
            select(
                Conversation,
                func.coalesce(msg_count_sub.c.msg_count, 0).label("msg_count"),
            )
            .outerjoin(msg_count_sub, Conversation.id == msg_count_sub.c.conversation_id)
            .where(*conditions)
            .order_by(desc(Conversation.is_pinned), desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )

        total_query = select(func.count(Conversation.id)).where(*conditions)
        total_result = await db.execute(total_query)
        total = total_result.scalar_one()

        result = await db.execute(query)
        rows = result.all()

        items = []
        for conv, count in rows:
            items.append(
                ConversationOut(
                    id=conv.id,
                    user_id=conv.user_id,
                    title=conv.title,
                    summary=conv.summary,
                    model=conv.model,
                    is_pinned=conv.is_pinned,
                    is_archived=conv.is_archived,
                    message_count=count,
                    created_at=conv.created_at,
                    updated_at=conv.updated_at,
                )
            )

        return ConversationListOut(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_conversation_detail(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> ConversationDetailOut:
        """Retrieve a conversation with full message history."""
        conversation = await self.get_conversation_or_404(
            db, conversation_id, user_id=user_id, load_messages=True
        )

        messages_out = [
            ChatMessageOut.model_validate(msg) for msg in conversation.messages
        ]

        return ConversationDetailOut(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            summary=conversation.summary,
            model=conversation.model,
            is_pinned=conversation.is_pinned,
            is_archived=conversation.is_archived,
            message_count=len(messages_out),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=messages_out,
        )

    async def update_conversation(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        data: ConversationUpdateIn,
        user_id: Optional[uuid.UUID] = None,
    ) -> Conversation:
        """Update conversation title, pinned status, or archived status."""
        conversation = await self.get_conversation_or_404(
            db, conversation_id, user_id=user_id
        )

        if data.title is not None:
            conversation.title = data.title.strip()
        if data.is_pinned is not None:
            conversation.is_pinned = data.is_pinned
        if data.is_archived is not None:
            conversation.is_archived = data.is_archived

        conversation.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Delete conversation and all cascaded messages."""
        conversation = await self.get_conversation_or_404(
            db, conversation_id, user_id=user_id
        )
        await db.delete(conversation)
        await db.commit()

    async def get_messages(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ChatMessage]:
        """Fetch messages of a conversation ordered chronologically."""
        await self.get_conversation_or_404(db, conversation_id, user_id=user_id)

        stmt = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def send_message_sync(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        data: MessageCreateIn,
        user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[ChatMessage, ChatMessage]:
        """Add user message and generate assistant response synchronously."""
        conversation = await self.get_conversation_or_404(
            db, conversation_id, user_id=user_id, load_messages=True
        )

        # Auto-title conversation if it still has default title
        if conversation.title == "New Conversation":
            conversation.title = data.content[:50].strip() + ("..." if len(data.content) > 50 else "")

        # Metadata including attachments
        metadata: Dict[str, Any] = data.metadata or {}
        if data.attachments:
            metadata["attachments"] = [a.model_dump() for a in data.attachments]

        # 1. Persist user message
        user_msg = ChatMessage(
            conversation_id=conversation.id,
            sender_type="user",
            content=data.content,
            model_name=data.model or conversation.model,
            metadata_json=metadata,
        )
        db.add(user_msg)
        await db.flush()

        # 2. Build dialogue history for AI context
        context_messages = [
            {"role": msg.sender_type, "content": msg.content}
            for msg in conversation.messages
        ]
        context_messages.append({"role": "user", "content": data.content})

        # 3. Call AI provider
        ai_res = await self.provider.generate_response(
            messages=context_messages,
            system_prompt=KHOJAI_SYSTEM_PROMPT,
            model=data.model or conversation.model,
        )

        # 4. Persist assistant reply
        assistant_msg = ChatMessage(
            conversation_id=conversation.id,
            sender_type="assistant",
            content=ai_res.content,
            model_name=ai_res.model_name,
            token_count=ai_res.token_count,
            metadata_json=ai_res.metadata,
        )
        db.add(assistant_msg)

        conversation.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(user_msg)
        await db.refresh(assistant_msg)

        return user_msg, assistant_msg

    async def stream_message_sse(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        data: MessageCreateIn,
        user_id: Optional[uuid.UUID] = None,
    ) -> AsyncIterator[str]:
        """Stream assistant response via Server-Sent Events (SSE) and persist on completion."""
        conversation = await self.get_conversation_or_404(
            db, conversation_id, user_id=user_id, load_messages=True
        )

        if conversation.title == "New Conversation":
            conversation.title = data.content[:50].strip() + ("..." if len(data.content) > 50 else "")

        metadata: Dict[str, Any] = data.metadata or {}
        if data.attachments:
            metadata["attachments"] = [a.model_dump() for a in data.attachments]

        # Persist user message immediately
        user_msg = ChatMessage(
            conversation_id=conversation.id,
            sender_type="user",
            content=data.content,
            model_name=data.model or conversation.model,
            metadata_json=metadata,
        )
        db.add(user_msg)
        await db.commit()

        # Context
        context_messages = [
            {"role": msg.sender_type, "content": msg.content}
            for msg in conversation.messages
        ]
        context_messages.append({"role": "user", "content": data.content})

        accumulated_chunks: List[str] = []
        model_used = data.model or conversation.model or "khojai-model"

        try:
            async for token in self.provider.stream_response(
                messages=context_messages,
                system_prompt=KHOJAI_SYSTEM_PROMPT,
                model=model_used,
            ):
                accumulated_chunks.append(token)
                chunk_payload = json.dumps({"token": token, "done": False})
                yield f"event: token\ndata: {chunk_payload}\n\n"

            full_content = "".join(accumulated_chunks)
            assistant_msg = ChatMessage(
                conversation_id=conversation.id,
                sender_type="assistant",
                content=full_content,
                model_name=model_used,
                token_count=int(len(full_content.split()) * 1.3),
                metadata_json={"streamed": True, "provider": getattr(self.provider, "default_model", "ai")},
            )
            db.add(assistant_msg)
            conversation.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(assistant_msg)

            done_payload = json.dumps({
                "message_id": str(assistant_msg.id),
                "content": full_content,
                "model": model_used,
                "done": True,
                "finish_reason": "stop",
            })
            yield f"event: done\ndata: {done_payload}\n\n"

        except Exception as exc:
            logger.exception("Error streaming chat response: %s", exc)
            err_payload = json.dumps({"error": str(exc), "done": True})
            yield f"event: error\ndata: {err_payload}\n\n"

    async def regenerate_response(
        self,
        db: AsyncSession,
        conversation_id: uuid.UUID,
        message_id: Optional[uuid.UUID] = None,
        model: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> ChatMessage:
        """Regenerate the latest (or designated) assistant response."""
        conversation = await self.get_conversation_or_404(
            db, conversation_id, user_id=user_id, load_messages=True
        )

        if not conversation.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot regenerate on an empty conversation.",
            )

        target_idx: Optional[int] = None
        if message_id:
            for idx, msg in enumerate(conversation.messages):
                if msg.id == message_id:
                    if msg.sender_type != "assistant":
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Can only regenerate assistant messages.",
                        )
                    target_idx = idx
                    break
            if target_idx is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Message '{message_id}' not found in conversation.",
                )
        else:
            # Find the latest assistant message
            for idx in range(len(conversation.messages) - 1, -1, -1):
                if conversation.messages[idx].sender_type == "assistant":
                    target_idx = idx
                    break
            if target_idx is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No assistant message found to regenerate.",
                )

        # Context messages up to the target message
        context_messages = [
            {"role": msg.sender_type, "content": msg.content}
            for msg in conversation.messages[:target_idx]
        ]

        # Generate new answer
        used_model = model or conversation.model
        ai_res = await self.provider.generate_response(
            messages=context_messages,
            system_prompt=KHOJAI_SYSTEM_PROMPT,
            model=used_model,
        )

        # Update existing message or replace it
        target_msg = conversation.messages[target_idx]
        target_msg.content = ai_res.content
        target_msg.model_name = ai_res.model_name
        target_msg.token_count = ai_res.token_count
        target_msg.metadata_json = {**target_msg.metadata_json, **ai_res.metadata, "regenerated_at": datetime.now(timezone.utc).isoformat()}

        conversation.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(target_msg)
        return target_msg


chat_service = ChatService()
