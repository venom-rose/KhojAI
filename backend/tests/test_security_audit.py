import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ai.providers.gemini_provider import GeminiProvider
from backend.app.config.settings import Settings
from backend.app.main import app
from backend.app.models.chat import Conversation, ChatMessage
from backend.app.models.document import Document
from backend.app.models.user import User
from backend.app.security.jwt import create_access_token
from backend.app.security.password import hash_password


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    """Verify that HTTP response includes mandatory security headers."""
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert "x-xss-protection" in res.headers
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_cross_tenant_conversation_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify that user B and unauthenticated callers cannot access or delete user A's conversation."""
    # Create User A
    user_a = User(
        email="usera_audit@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="User A",
        role="traveler",
    )
    # Create User B
    user_b = User(
        email="userb_audit@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="User B",
        role="traveler",
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()
    await db_session.refresh(user_a)
    await db_session.refresh(user_b)

    # Create private conversation for User A
    conv_a = Conversation(
        user_id=user_a.id,
        title="User A Private Journey",
        model="khojai-explorer-v1",
    )
    db_session.add(conv_a)
    await db_session.commit()
    await db_session.refresh(conv_a)

    # 1. Unauthenticated request to User A's conversation MUST be denied (403 or 401)
    res_anon = await client.get(f"/api/v1/chat/conversations/{conv_a.id}")
    assert res_anon.status_code == 403, f"Expected 403 Forbidden for anon, got {res_anon.status_code}"

    # 2. User B attempting to access User A's conversation MUST be denied (403)
    token_b = create_access_token(subject=user_b.id, email=user_b.email, role=user_b.role)
    headers_b = {"Authorization": f"Bearer {token_b}"}
    res_b = await client.get(f"/api/v1/chat/conversations/{conv_a.id}", headers=headers_b)
    assert res_b.status_code == 403, f"Expected 403 Forbidden for User B, got {res_b.status_code}"

    # 3. User B attempting to delete User A's conversation MUST be denied (403)
    res_del = await client.delete(f"/api/v1/chat/conversations/{conv_a.id}", headers=headers_b)
    assert res_del.status_code == 403, f"Expected 403 Forbidden for User B delete, got {res_del.status_code}"

    # 4. User A accessing their own conversation MUST succeed (200)
    token_a = create_access_token(subject=user_a.id, email=user_a.email, role=user_a.role)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    res_a = await client.get(f"/api/v1/chat/conversations/{conv_a.id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["id"] == str(conv_a.id)


@pytest.mark.asyncio
async def test_cross_tenant_document_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify that user B and unauthenticated callers cannot read or delete user A's private document."""
    # Create User A & User B
    user_a = User(
        email="doc_usera@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Doc User A",
        role="traveler",
    )
    user_b = User(
        email="doc_userb@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Doc User B",
        role="traveler",
    )
    db_session.add_all([user_a, user_b])
    await db_session.commit()
    await db_session.refresh(user_a)
    await db_session.refresh(user_b)

    # User A private document
    doc_a = Document(
        user_id=user_a.id,
        title="User A Secret Route Map",
        document_type="guide",
        status="ready",
        original_filename="secret_route.txt",
        file_size=1024,
    )
    db_session.add(doc_a)
    await db_session.commit()
    await db_session.refresh(doc_a)

    # 1. Unauthenticated request MUST be rejected with 403 Forbidden
    res_anon = await client.get(f"/api/v1/documents/{doc_a.id}")
    assert res_anon.status_code == 403, f"Expected 403 for anon accessing private doc, got {res_anon.status_code}"

    # 2. User B request MUST be rejected with 403 Forbidden
    token_b = create_access_token(subject=user_b.id, email=user_b.email, role=user_b.role)
    headers_b = {"Authorization": f"Bearer {token_b}"}
    res_b = await client.get(f"/api/v1/documents/{doc_a.id}", headers=headers_b)
    assert res_b.status_code == 403, f"Expected 403 for User B accessing private doc, got {res_b.status_code}"

    # 3. User B cannot delete User A's document
    res_del = await client.delete(f"/api/v1/documents/{doc_a.id}", headers=headers_b)
    assert res_del.status_code == 403, f"Expected 403 for User B deleting private doc, got {res_del.status_code}"

    # 4. User A can access their own document
    token_a = create_access_token(subject=user_a.id, email=user_a.email, role=user_a.role)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    res_a = await client.get(f"/api/v1/documents/{doc_a.id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["id"] == str(doc_a.id)


@pytest.mark.asyncio
async def test_search_isolation_prevents_leakage(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify that search does not leak other users' private conversations or documents."""
    user = User(
        email="search_isolation@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Search User",
        role="traveler",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    conv = Conversation(
        user_id=user.id,
        title="Classified Expedition Notes 999",
        model="khojai-explorer-v1",
    )
    db_session.add(conv)
    await db_session.commit()

    # Anonymous search query for "Classified Expedition"
    res_anon = await client.get("/api/v1/search?q=Classified+Expedition")
    assert res_anon.status_code == 200
    data = res_anon.json()
    assert len(data["conversations"]) == 0, "Anonymous search leaked private user conversation!"


def test_jwt_secret_length_validation():
    """Verify that settings reject insecure JWT secrets shorter than 32 characters."""
    with pytest.raises(ValueError, match="JWT_SECRET must be at least 32 characters long"):
        Settings(JWT_SECRET="too_short_key")


@pytest.mark.asyncio
async def test_gemini_header_auth(monkeypatch):
    """Verify that GeminiProvider passes API key via x-goog-api-key header and not in query string."""
    provider = GeminiProvider(api_key="test_api_key_12345", default_model="gemini-1.5-flash")

    recorded_requests = []

    async def mock_post(client, url, *args, **kwargs):
        recorded_requests.append({"url": str(url), "headers": kwargs.get("headers", {})})

        class MockResponse:
            status_code = 200

            def json(self):
                return {
                    "candidates": [{
                        "content": {"parts": [{"text": "Mocked test response"}]},
                        "finishReason": "STOP",
                    }],
                    "usageMetadata": {"totalTokenCount": 10},
                }

        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    response = await provider.generate_response(messages=[{"role": "user", "content": "Hello"}])
    assert response.content == "Mocked test response"
    assert len(recorded_requests) == 1

    req = recorded_requests[0]
    # URL must not contain the api key
    assert "key=" not in req["url"], f"API key was exposed in query string: {req['url']}"
    # Header must contain the api key
    assert req["headers"].get("x-goog-api-key") == "test_api_key_12345"
