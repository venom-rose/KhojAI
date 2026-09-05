import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.destination import Destination, DestinationTag
from backend.app.security.rate_limiter import SlidingWindowRateLimiter


@pytest.mark.asyncio
async def test_search_rate_limiter_logic():
    """Verify sliding-window rate limiter triggers 429 when max requests exceeded."""
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)
    
    class FakeRequest:
        def __init__(self, ip):
            self.headers = {"x-forwarded-for": ip}
            self.client = None

    req = FakeRequest("192.168.1.100")
    limiter.check_rate_limit(req)
    limiter.check_rate_limit(req)
    limiter.check_rate_limit(req)

    # 4th request within window raises 429
    with pytest.raises(Exception) as exc_info:
        limiter.check_rate_limit(req)
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_destination_search_keyword_and_filters(client: AsyncClient, db_session: AsyncSession):
    """Test destination search with keywords and faceted filters."""
    # Seed destinations
    d1 = Destination(
        slug="ziro-valley-search-test",
        name="Ziro Valley",
        state="Arunachal Pradesh",
        region="Northeast",
        category="Nature · Culture",
        best_season="Oct – Nov",
        budget="₹₹",
        trust_score=95,
        description="A peaceful high-altitude plateau with Apatani pine forests.",
        image_url="https://images.unsplash.com/ziro.jpg",
    )
    d2 = Destination(
        slug="spiti-valley-search-test",
        name="Spiti Valley",
        state="Himachal Pradesh",
        region="Himalayas",
        category="Outdoors · High Altitude",
        best_season="Jun – Sep",
        budget="₹",
        trust_score=88,
        description="Cold desert mountain valley with ancient Buddhist monasteries.",
        image_url="https://images.unsplash.com/spiti.jpg",
    )
    db_session.add_all([d1, d2])
    await db_session.commit()

    # 1. Keyword match on Name
    res1 = await client.get("/api/v1/search/destinations?q=Ziro")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 1
    assert data1["items"][0]["name"] == "Ziro Valley"
    assert data1["items"][0]["relevance_score"] >= 0.8

    # 2. Region filter
    res2 = await client.get("/api/v1/search/destinations?region=Himalayas")
    assert res2.status_code == 200
    data2 = res2.json()
    assert any(item["name"] == "Spiti Valley" for item in data2["items"])
    assert all(item["region"] == "Himalayas" for item in data2["items"])

    # 3. Budget filter
    res3 = await client.get("/api/v1/search/destinations?budget=₹")
    assert res3.status_code == 200
    data3 = res3.json()
    assert any(item["name"] == "Spiti Valley" for item in data3["items"])

    # 4. Sorting: Most Trusted
    res4 = await client.get("/api/v1/search/destinations?sort=Most+Trusted")
    assert res4.status_code == 200
    data4 = res4.json()
    scores = [item["trust_score"] for item in data4["items"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_hybrid_document_search(client: AsyncClient):
    """Test hybrid search over ingested documents combining keywords and semantic vectors."""
    # 1. Ingest guide document
    content = (
        "Spiti Valley High Altitude Guide\n\n"
        "Kunzum Pass connects the Kullu Valley and Lahaul Valley with the Spiti Valley. "
        "At 4,551 meters, it offers breathtaking views of the Bara-Shigri glacier."
    )
    files = {"file": ("spiti_passes.txt", content.encode("utf-8"), "text/plain")}
    upload_res = await client.post("/api/v1/documents?process_async=false", files=files)
    assert upload_res.status_code == 201

    # 2. Hybrid Search for "Kunzum Pass glacier"
    search_res = await client.get("/api/v1/search/documents?q=Kunzum+Pass+glacier")
    assert search_res.status_code == 200
    data = search_res.json()
    assert data["total"] >= 1
    top_hit = data["items"][0]
    assert "Kunzum" in top_hit["content"]
    assert top_hit["similarity"] >= 0.1
    assert top_hit["relevance_score"] >= 0.3


@pytest.mark.asyncio
async def test_conversation_search_and_isolation(client: AsyncClient):
    """Test searching conversation messages and enforcing user privacy isolation."""
    # Register User A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "searcher_a@example.com", "password": "Password123!", "full_name": "Searcher A"},
    )
    token_a = res_a.json()["access_token"]

    # Register User B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "searcher_b@example.com", "password": "Password123!", "full_name": "Searcher B"},
    )
    token_b = res_b.json()["access_token"]

    # User A creates a conversation with a specific inquiry
    create_res = await client.post(
        "/api/v1/chat/conversations",
        json={
            "title": "Secret Wayanad Journey",
            "initial_message": "Tell me about bamboo homestays in Tholpetty corridor",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_res.status_code == 201

    # User A searches for "Tholpetty" -> finds conversation with matched message snippet
    search_a = await client.get(
        "/api/v1/search/conversations?q=Tholpetty",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert search_a.status_code == 200
    data_a = search_a.json()
    assert data_a["total"] == 1
    assert data_a["items"][0]["title"] == "Secret Wayanad Journey"
    assert "Tholpetty" in data_a["items"][0]["matched_message"]

    # User B searches for "Tholpetty" -> 0 hits (privacy isolation preserved)
    search_b = await client.get(
        "/api/v1/search/conversations?q=Tholpetty",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert search_b.status_code == 200
    data_b = search_b.json()
    assert data_b["total"] == 0


@pytest.mark.asyncio
async def test_global_omnisearch(client: AsyncClient, db_session: AsyncSession):
    """Test omnisearch returning categorized hits across destinations, documents, and conversations."""
    # Seed destination
    dest = Destination(
        slug="khonoma-green-village",
        name="Khonoma",
        state="Nagaland",
        region="Northeast",
        category="Heritage · Village",
        best_season="Oct – Apr",
        budget="₹₹",
        trust_score=92,
        description="Asia's first green village, home to the Angami community.",
        image_url="https://images.unsplash.com/khonoma.jpg",
    )
    db_session.add(dest)
    await db_session.commit()

    res = await client.get("/api/v1/search?q=Khonoma")
    assert res.status_code == 200
    data = res.json()
    assert data["query"] == "Khonoma"
    assert data["total_hits"] >= 1
    assert any(d["name"] == "Khonoma" for d in data["destinations"])


@pytest.mark.asyncio
async def test_search_validation_errors(client: AsyncClient):
    """Test validation errors for missing or invalid query parameters."""
    # Missing query parameter 'q' on global search
    res = await client.get("/api/v1/search")
    assert res.status_code == 422
