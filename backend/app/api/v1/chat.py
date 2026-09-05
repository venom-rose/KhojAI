import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_optional_current_user
from backend.app.database.session import get_db
from backend.app.models.user import User
from backend.app.schemas.chat import (
    ChatMessageOut,
    ConversationCreateIn,
    ConversationDetailOut,
    ConversationListOut,
    ConversationOut,
    ConversationUpdateIn,
    MessageCreateIn,
    MessageRegenerateIn,
)
from backend.app.services.chat_service import chat_service

router = APIRouter(prefix="/chat", tags=["Chat & Intelligence"])


@router.post(
    "/conversations",
    response_model=ConversationDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create conversation",
    description="Initialize a new travel intelligence chat conversation with optional initial inquiry.",
)
async def create_conversation(
    data: ConversationCreateIn,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    conv, user_msg, assistant_msg = await chat_service.create_conversation(
        db=db, data=data, user_id=user_id
    )
    return await chat_service.get_conversation_detail(db, conv.id, user_id=user_id)


@router.get(
    "/conversations",
    response_model=ConversationListOut,
    summary="Retrieve conversations",
    description="List active conversations with optional pagination, search filtering, and archive inclusion.",
)
async def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    include_archived: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await chat_service.list_conversations(
        db=db,
        user_id=user_id,
        limit=limit,
        offset=offset,
        search=search,
        include_archived=include_archived,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailOut,
    summary="Retrieve conversation details",
    description="Fetch a conversation by ID along with its full chronological message history.",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    return await chat_service.get_conversation_detail(
        db=db, conversation_id=conversation_id, user_id=user_id
    )


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationOut,
    summary="Rename or update conversation",
    description="Update conversation metadata including title, pin state, or archive status.",
)
async def update_conversation(
    conversation_id: uuid.UUID,
    data: ConversationUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    conv = await chat_service.update_conversation(
        db=db, conversation_id=conversation_id, data=data, user_id=user_id
    )
    return ConversationOut.model_validate(conv)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete conversation",
    description="Permanently delete a conversation and all its associated messages.",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    await chat_service.delete_conversation(
        db=db, conversation_id=conversation_id, user_id=user_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[ChatMessageOut],
    summary="Retrieve conversation messages",
    description="Retrieve paginated messages for a conversation.",
)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    messages = await chat_service.get_messages(
        db=db,
        conversation_id=conversation_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    return [ChatMessageOut.model_validate(m) for m in messages]


@router.post(
    "/conversations/{conversation_id}/messages",
    summary="Send message",
    description="Submit a new message to the conversation. Set stream=true or send Accept: text/event-stream for SSE.",
)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreateIn,
    stream: Optional[bool] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    should_stream = stream if stream is not None else data.stream

    if should_stream:
        return StreamingResponse(
            chat_service.stream_message_sse(
                db=db, conversation_id=conversation_id, data=data, user_id=user_id
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    _, assistant_msg = await chat_service.send_message_sync(
        db=db, conversation_id=conversation_id, data=data, user_id=user_id
    )
    return ChatMessageOut.model_validate(assistant_msg)


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/regenerate",
    response_model=ChatMessageOut,
    summary="Regenerate message response",
    description="Regenerate a specific assistant response in the conversation history.",
)
async def regenerate_specific_message(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    data: MessageRegenerateIn = MessageRegenerateIn(),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    msg = await chat_service.regenerate_response(
        db=db,
        conversation_id=conversation_id,
        message_id=message_id,
        model=data.model,
        user_id=user_id,
    )
    return ChatMessageOut.model_validate(msg)


@router.post(
    "/conversations/{conversation_id}/regenerate",
    response_model=ChatMessageOut,
    summary="Regenerate latest assistant response",
    description="Regenerate the latest assistant response in the conversation history.",
)
async def regenerate_latest_message(
    conversation_id: uuid.UUID,
    data: MessageRegenerateIn = MessageRegenerateIn(),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    user_id = current_user.id if current_user else None
    msg = await chat_service.regenerate_response(
        db=db,
        conversation_id=conversation_id,
        message_id=None,
        model=data.model,
        user_id=user_id,
    )
    return ChatMessageOut.model_validate(msg)
