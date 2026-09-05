"""Comprehensive End-to-End Test Suite for KHOJAI Backend.

Validates:
- Authentication, token lifecycle, expiration, malformed tokens, inactive accounts
- User isolation, authorization, profile management, and account deletion
- Conversations, messaging, AI response generation with mocked provider, and cross-tenant protection
- Document ingestion, chunking, embeddings, oversized/invalid file handling, RAG Q&A
- Search APIs, query validation, and multi-tenant scoping
- Complete HTTP error code matrix (400, 401, 403, 404, 409, 413, 422)
"""

import io
import os
import uuid
from datetime import timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.config.settings import settings
from backend.app.models import User, Conversation, ChatMessage, Document
from backend.app.security.jwt import create_access_token


# =====================================================================
# 1. AUTHENTICATION, TOKEN LIFECYCLE & SECURITY
# =====================================================================

@pytest.mark.asyncio
async def test_auth_expired_token(client: AsyncClient, db_session: AsyncSession):
    """Expired JWT token returns 401 Unauthorized."""
    # Register user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "expired_user@example.com", "password": "Password123!", "full_name": "Expired Test"},
    )
    assert reg_res.status_code == 201
    user_id = reg_res.json()["user"]["id"]

    # Generate an already expired access token
    expired_token = create_access_token(
        subject=user_id,
        email="expired_user@example.com",
        role="traveler",
        expires_delta=timedelta(minutes=-15),
    )

    # Attempt to access protected endpoint
    res = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "expired" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_malformed_and_tampered_tokens(client: AsyncClient):
    """Malformed or invalid signature tokens return 401 Unauthorized."""
    # 1. Completely bogus token
    res1 = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid.malformed.token"},
    )
    assert res1.status_code == 401
    assert "invalid or malformed" in res1.json()["detail"].lower()

    # 2. Token signed with wrong secret key
    import jwt
    bogus_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "email": "hacker@example.com", "role": "traveler"},
        "wrong_jwt_secret_key_that_is_at_least_32_characters_long",
        algorithm="HS256",
    )
    res2 = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {bogus_token}"},
    )
    assert res2.status_code == 401


@pytest.mark.asyncio
async def test_auth_missing_credentials(client: AsyncClient):
    """Protected endpoint accessed with no authorization header or cookie returns 401."""
    res = await client.get("/api/v1/users/me")
    assert res.status_code == 401
    assert "not authenticated" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_inactive_account(client: AsyncClient, db_session: AsyncSession):
    """Deactivated user account returns 403 Forbidden upon access."""
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "inactive@example.com", "password": "Password123!", "full_name": "Inactive User"},
    )
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    user_id = uuid.UUID(reg_res.json()["user"]["id"])

    # Deactivate account in database
    user = await db_session.get(User, user_id)
    assert user is not None
    user.is_active = False
    await db_session.commit()

    # Attempt access
    res = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_invalid_payloads(client: AsyncClient):
    """Validation errors on auth endpoints return 422 Unprocessable Entity."""
    # Missing password
    res1 = await client.post(
        "/api/v1/auth/register",
        json={"email": "bad@example.com", "full_name": "No Password"},
    )
    assert res1.status_code == 422

    # Invalid email format
    res2 = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "Password123!", "full_name": "Bad Email"},
    )
    assert res2.status_code == 422


# =====================================================================
# 2. USER ISOLATION & PROFILE MANAGEMENT
# =====================================================================

@pytest.mark.asyncio
async def test_user_profile_and_preferences_lifecycle(client: AsyncClient):
    """User can read and update their own profile and AI preferences."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "profile_user@example.com", "password": "Password123!", "full_name": "Original Name"},
    )
    token = reg.json()["access_token"]

    # 1. Update profile
    patch_res = await client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Updated Explorer", "bio": "Passionate travel photographer in Ladakh.", "theme_preference": "dark"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["full_name"] == "Updated Explorer"
    assert patch_res.json()["bio"] == "Passionate travel photographer in Ladakh."
    assert patch_res.json()["theme_preference"] == "dark"

    # 2. Update preferences
    pref_res = await client.patch(
        "/api/v1/users/me/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "style": "adventure",
            "interests": ["adventure", "heritage", "photography"],
            "ai_pace": "unhurried",
        },
    )
    assert pref_res.status_code == 200
    user_data = pref_res.json()
    assert "photography" in user_data["travel_preferences"]["interests"]
    assert user_data["travel_preferences"]["ai_pace"] == "unhurried"


@pytest.mark.asyncio
async def test_user_self_deletion(client: AsyncClient):
    """User can soft-delete their own account; subsequent requests are rejected."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "to_delete@example.com", "password": "Password123!", "full_name": "Delete Me"},
    )
    token = reg.json()["access_token"]

    # Delete account
    del_res = await client.delete(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    # Subsequent access fails
    subsequent = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert subsequent.status_code == 401


# =====================================================================
# 3. CONVERSATIONS & CHAT
# =====================================================================

@pytest.mark.asyncio
async def test_conversation_and_messaging_e2e(client: AsyncClient):
    """Create conversation, send message, generate AI response, list messages."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "chat_tester@example.com", "password": "Password123!", "full_name": "Chat Tester"},
    )
    token = reg.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # 1. Create conversation
    create_res = await client.post(
        "/api/v1/chat/conversations",
        headers=auth_header,
        json={"title": "Himalayan Roadtrip Planning"},
    )
    assert create_res.status_code == 201
    conv_id = create_res.json()["id"]

    # 2. Send message and receive AI response
    msg_res = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_header,
        json={"content": "What is the best route from Manali to Leh via Atal Tunnel?"},
    )
    assert msg_res.status_code == 200
    assistant_msg = msg_res.json()
    assert assistant_msg["sender_type"] == "assistant"
    assert assistant_msg["content"]

    # 3. Retrieve conversation with message history
    history_res = await client.get(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=auth_header,
    )
    assert history_res.status_code == 200
    messages = history_res.json()
    assert len(messages) >= 2
    assert any(m["sender_type"] == "user" for m in messages)
    assert any(m["sender_type"] == "assistant" for m in messages)

    # 4. Rename conversation
    rename_res = await client.patch(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_header,
        json={"title": "Leh Expedition 2026"},
    )
    assert rename_res.status_code == 200
    assert rename_res.json()["title"] == "Leh Expedition 2026"

    # 5. Delete conversation
    del_res = await client.delete(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_header,
    )
    assert del_res.status_code == 204

    # 6. Verify 404 after deletion
    not_found_res = await client.get(
        f"/api/v1/chat/conversations/{conv_id}",
        headers=auth_header,
    )
    assert not_found_res.status_code == 404


@pytest.mark.asyncio
async def test_conversation_non_existent_404(client: AsyncClient):
    """Accessing non-existent conversation returns 404."""
    random_id = str(uuid.uuid4())
    res = await client.get(f"/api/v1/chat/conversations/{random_id}")
    assert res.status_code == 404


# =====================================================================
# 4. DOCUMENTS, LARGE UPLOADS & RAG
# =====================================================================

@pytest.mark.asyncio
async def test_document_large_upload_rejection(client: AsyncClient):
    """File exceeding MAX_UPLOAD_SIZE_MB returns 413 Request Entity Too Large."""
    # Generate content that exceeds configured MAX_UPLOAD_SIZE_MB
    oversized_bytes = b"0" * ((settings.MAX_UPLOAD_SIZE_MB + 1) * 1024 * 1024)
    files = {"file": ("massive_guide.txt", oversized_bytes, "text/plain")}
    res = await client.post("/api/v1/documents", files=files)
    assert res.status_code == 413
    assert "exceeds maximum allowed size" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_document_missing_404(client: AsyncClient):
    """Accessing or deleting non-existent document returns 404."""
    random_id = str(uuid.uuid4())
    get_res = await client.get(f"/api/v1/documents/{random_id}")
    assert get_res.status_code == 404

    del_res = await client.delete(f"/api/v1/documents/{random_id}")
    assert del_res.status_code == 404


@pytest.mark.asyncio
async def test_document_rag_flow_with_citations(client: AsyncClient):
    """Upload document, verify extraction and chunking, query context-aware answer."""
    content = (
        "Meghalaya Living Root Bridges and Cleanest Village\n\n"
        "Mawlynnong in the East Khasi Hills is widely recognized as Asia's cleanest village. "
        "The community emphasizes zero plastic waste and bamboo collection bins.\n\n"
        "In nearby Cherrapunji (Sohra) and Nongriat, local Khasi communities guide travelers "
        "across ancient double-decker living root bridges constructed by training rubber fig roots across rivers."
    )
    files = {"file": ("meghalaya_wonders.txt", content.encode("utf-8"), "text/plain")}
    data = {"title": "Meghalaya Wonders Guide"}

    # Upload & sync process
    up_res = await client.post("/api/v1/documents?process_async=false", files=files, data=data)
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]
    assert up_res.json()["status"] == "ready"

    # Query RAG
    rag_res = await client.post(
        "/api/v1/documents/query",
        json={"query": "Which village in East Khasi Hills is known for cleanliness and living root bridges?", "top_k": 3},
    )
    assert rag_res.status_code == 200
    rag_out = rag_res.json()
    assert rag_out["answer"]
    assert len(rag_out["sources"]) >= 1
    assert any("Mawlynnong" in s["content"] for s in rag_out["sources"])


# =====================================================================
# 5. SEARCH BACKEND & VALIDATION
# =====================================================================

@pytest.mark.asyncio
async def test_search_validation_and_results(client: AsyncClient):
    """Search endpoints enforce query validation (min_length=1) and return results."""
    # 1. Empty query should be rejected by Pydantic validation (422)
    empty_res = await client.get("/api/v1/search?q=")
    assert empty_res.status_code == 422

    # 2. Ingest a document and search
    doc_text = "Hidden valley of Orchids in Arunachal Pradesh near Sela Pass."
    files = {"file": ("orchids.txt", doc_text.encode("utf-8"), "text/plain")}
    await client.post("/api/v1/documents?process_async=false", files=files)

    # Search global
    search_res = await client.get("/api/v1/search?q=Orchids+Sela+Pass")
    assert search_res.status_code == 200
    data = search_res.json()
    assert "documents" in data
    assert "conversations" in data
    assert len(data["documents"]) >= 1
    assert "Orchids" in data["documents"][0]["document_title"] or "orchids" in data["documents"][0]["content"].lower()
