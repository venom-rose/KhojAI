import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ai.factory import get_ai_provider
from backend.app.ai.providers.local_provider import LocalProvider
from backend.app.ai.providers.gemini_provider import GeminiProvider
from backend.app.ai.providers.openai_provider import OpenAIProvider
from backend.app.security.jwt import create_access_token
from backend.app.services.user_service import user_service
from backend.app.schemas.auth import UserRegisterIn


@pytest.mark.asyncio
async def test_ai_provider_factory_and_switching():
    """Verify AI provider factory instantiates correct providers."""
    local_p = get_ai_provider("local")
    assert isinstance(local_p, LocalProvider)

    gemini_p = get_ai_provider("gemini")
    assert isinstance(gemini_p, GeminiProvider)

    openai_p = get_ai_provider("openai")
    assert isinstance(openai_p, OpenAIProvider)

    # Test LocalProvider response generation and streaming
    res = await local_p.generate_response(
        messages=[{"role": "user", "content": "Tell me about Ziro Valley in Arunachal Pradesh"}]
    )
    assert res.content
    assert "Ziro Valley" in res.content
    assert res.model_name
    assert "citations" in res.metadata

    # Test streaming
    tokens = []
    async for token in local_p.stream_response(
        messages=[{"role": "user", "content": "Spiti Valley offbeat route"}]
    ):
        tokens.append(token)
    assert len(tokens) > 0
    assert "Spiti" in "".join(tokens)


@pytest.mark.asyncio
async def test_create_conversation_anonymous(client: AsyncClient):
    """Anonymous/guest user can start a conversation."""
    response = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Offbeat Northeast Inquiry", "model": "khojai-local-v1"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Offbeat Northeast Inquiry"
    assert data["model"] == "khojai-local-v1"
    assert data["messages"] == []
    assert data["message_count"] == 0
    assert "id" in data


@pytest.mark.asyncio
async def test_create_conversation_with_initial_message(client: AsyncClient):
    """Creating a conversation with an initial inquiry generates user & assistant messages."""
    response = await client.post(
        "/api/v1/chat/conversations",
        json={
            "title": "New Conversation",
            "initial_message": "What is the best time to visit Ziro Valley homestays?",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["sender_type"] == "user"
    assert data["messages"][0]["content"] == "What is the best time to visit Ziro Valley homestays?"
    assert data["messages"][1]["sender_type"] == "assistant"
    assert "Ziro" in data["messages"][1]["content"]
    assert data["message_count"] == 2


@pytest.mark.asyncio
async def test_send_message_sync(client: AsyncClient):
    """Sending a message synchronously returns the assistant reply and persists both."""
    # 1. Create conversation
    create_res = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Spiti Monasteries"},
    )
    conv_id = create_res.json()["id"]

    # 2. Send user message
    msg_res = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={
            "content": "Can you recommend a slow high-altitude itinerary for Spiti Valley?",
            "stream": False,
        },
    )
    assert msg_res.status_code == 200
    reply = msg_res.json()
    assert reply["sender_type"] == "assistant"
    assert "Spiti" in reply["content"]
    assert reply["conversation_id"] == conv_id

    # 3. Verify conversation detail contains both user and assistant messages
    detail_res = await client.get(f"/api/v1/chat/conversations/{conv_id}")
    assert detail_res.status_code == 200
    messages = detail_res.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["sender_type"] == "user"
    assert messages[1]["sender_type"] == "assistant"


@pytest.mark.asyncio
async def test_send_message_streaming_sse(client: AsyncClient):
    """Sending a message with stream=True returns Server-Sent Events (SSE) stream and persists."""
    # 1. Create conversation
    create_res = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "Meghalaya Living Bridges"},
    )
    conv_id = create_res.json()["id"]

    # 2. Send message with stream=True
    msg_res = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages?stream=true",
        json={"content": "Tell me about living root bridges and quiet villages in Meghalaya."},
    )
    assert msg_res.status_code == 200
    assert "text/event-stream" in msg_res.headers.get("content-type", "")

    stream_content = msg_res.text
    assert "event: token" in stream_content
    assert "event: done" in stream_content
    assert "Meghalaya" in stream_content

    # 3. Verify message is persisted in conversation
    detail_res = await client.get(f"/api/v1/chat/conversations/{conv_id}")
    messages = detail_res.json()["messages"]
    assert len(messages) == 2
    assert messages[1]["sender_type"] == "assistant"
    assert "Meghalaya" in messages[1]["content"]


@pytest.mark.asyncio
async def test_list_conversations_and_pagination(client: AsyncClient):
    """List conversations returns paginated summaries ordered with pinned items first."""
    # Create 3 conversations
    c1 = (await client.post("/api/v1/chat/conversations", json={"title": "Trip to Kerala"})).json()
    c2 = (await client.post("/api/v1/chat/conversations", json={"title": "Trip to Ladakh"})).json()
    c3 = (await client.post("/api/v1/chat/conversations", json={"title": "Trip to Coorg"})).json()

    # Pin c1
    await client.patch(f"/api/v1/chat/conversations/{c1['id']}", json={"is_pinned": True})

    # List conversations
    res = await client.get("/api/v1/chat/conversations?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 3
    # Pinned conversation should be first
    assert data["items"][0]["id"] == c1["id"]
    assert data["items"][0]["is_pinned"] is True

    # Search filter
    search_res = await client.get("/api/v1/chat/conversations?search=Kerala")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["title"] == "Trip to Kerala"


@pytest.mark.asyncio
async def test_update_conversation_rename(client: AsyncClient):
    """Update conversation title and archive status."""
    c = (await client.post("/api/v1/chat/conversations", json={"title": "Draft Title"})).json()
    conv_id = c["id"]

    patch_res = await client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        json={"title": "Renamed: Hidden Villages of Kumaon", "is_archived": True},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["title"] == "Renamed: Hidden Villages of Kumaon"
    assert updated["is_archived"] is True


@pytest.mark.asyncio
async def test_delete_conversation_cascades(client: AsyncClient):
    """Deleting conversation removes conversation and all associated messages."""
    c = (await client.post(
        "/api/v1/chat/conversations",
        json={"initial_message": "Inquiry before deletion"},
    )).json()
    conv_id = c["id"]

    # Delete conversation
    del_res = await client.delete(f"/api/v1/chat/conversations/{conv_id}")
    assert del_res.status_code == 204

    # Fetching deleted conversation returns 404
    get_res = await client.get(f"/api/v1/chat/conversations/{conv_id}")
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_regenerate_assistant_response(client: AsyncClient):
    """Regenerate latest assistant response."""
    # Create conversation with initial interaction
    c = (await client.post(
        "/api/v1/chat/conversations",
        json={"initial_message": "Recommend quiet homestays in Ziro"},
    )).json()
    conv_id = c["id"]
    initial_assistant_msg_id = c["messages"][1]["id"]

    # Call regenerate
    regen_res = await client.post(f"/api/v1/chat/conversations/{conv_id}/regenerate")
    assert regen_res.status_code == 200
    new_reply = regen_res.json()
    assert new_reply["sender_type"] == "assistant"
    assert "Ziro" in new_reply["content"]
    assert "regenerated_at" in new_reply["metadata_json"]


@pytest.mark.asyncio
async def test_user_conversation_isolation(client: AsyncClient):
    """User A cannot access or modify User B's conversation."""
    # Register User A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "usera@example.com",
            "password": "Password123!",
            "full_name": "User Alpha",
        },
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]

    # Register User B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "userb@example.com",
            "password": "Password123!",
            "full_name": "User Bravo",
        },
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]

    # User A creates a conversation
    create_res = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "User A Private Travel Plan"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    conv_id = create_res.json()["id"]

    # User A can access it
    ok_res = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert ok_res.status_code == 200

    # User B attempts to access User A's conversation -> 403 Forbidden
    forbidden_get = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_get.status_code == 403

    # User B attempts to delete User A's conversation -> 403 Forbidden
    forbidden_del = await client.delete(
        f"/api/v1/chat/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_del.status_code == 403


@pytest.mark.asyncio
async def test_nonexistent_conversation_returns_404(client: AsyncClient):
    """Accessing non-existent conversation returns 404."""
    random_id = uuid.uuid4()
    res = await client.get(f"/api/v1/chat/conversations/{random_id}")
    assert res.status_code == 404
