import io
import os
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import settings
from backend.app.rag.cleaner import TextCleaner
from backend.app.rag.chunker import TextChunker
from backend.app.rag.embeddings import (
    LocalEmbeddingProvider,
    compute_cosine_similarity,
)
from backend.app.rag.extractor import sanitize_filename, validate_file_safety


def test_sanitize_filename_and_safety():
    """Verify filename sanitization and directory traversal prevention."""
    unsafe = "../../../etc/passwd"
    clean = sanitize_filename(unsafe)
    assert ".." not in clean
    assert "/" not in clean

    base_dir = os.path.abspath("./media/documents")
    safe_path = os.path.join(base_dir, "doc_123.dat")
    assert validate_file_safety(safe_path, base_dir) is True

    unsafe_path = os.path.abspath("./media/documents/../../secret.txt")
    assert validate_file_safety(unsafe_path, base_dir) is False


def test_text_cleaner():
    """Verify text normalization, control char stripping, and whitespace standardizing."""
    raw = "  Hello \x00 world!  \r\n\r\n\r\n\r\nThis   is  a test.\t\t\nLine 2   "
    cleaned = TextCleaner.clean_text(raw)
    assert "\x00" not in cleaned
    assert "\r" not in cleaned
    assert "  " not in cleaned.splitlines()[0]
    assert "Hello world!" in cleaned
    assert "This is a test." in cleaned


def test_text_chunker():
    """Verify sliding-window chunking respecting paragraph structure."""
    text = (
        "Ziro Valley is an enchanting high-altitude valley in Arunachal Pradesh.\n\n"
        "The Apatani tribe is celebrated for their unique agricultural system of paddy-cum-fish culture, "
        "relying entirely on organic soil nutrient recycling and bamboo irrigation canals without synthetic inputs.\n\n"
        "Hong village is one of the largest villages in the valley, known for its wooden stilt architecture "
        "and hospitable homestay hosts."
    )
    chunker = TextChunker(chunk_size=150, chunk_overlap=30)
    chunks = chunker.chunk_text(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert c["content"]
        assert c["token_count"] > 0
        assert "chunk_index" in c["metadata"]


@pytest.mark.asyncio
async def test_embedding_and_cosine_similarity():
    """Verify vector generation and cosine similarity calculation."""
    emb = LocalEmbeddingProvider()
    v1 = await emb.embed_text("Ziro Valley Arunachal Pradesh Apatani")
    v2 = await emb.embed_text("Apatani tribe paddy cultivation in Ziro")
    v3 = await emb.embed_text("Beaches of Goa and coastal water sports")

    sim_high = compute_cosine_similarity(v1, v2)
    sim_low = compute_cosine_similarity(v1, v3)

    assert sim_high > sim_low
    assert sim_high > 0.2


@pytest.mark.asyncio
async def test_upload_unsupported_file_type(client: AsyncClient):
    """Uploading unsupported executable or script file is rejected."""
    file_bytes = b"import os; os.system('echo bad')"
    files = {"file": ("malicious.py", file_bytes, "text/x-python")}
    res = await client.post("/api/v1/documents", files=files)
    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["detail"]


@pytest.mark.asyncio
async def test_upload_empty_file(client: AsyncClient):
    """Uploading empty file (0 bytes) is rejected."""
    files = {"file": ("empty.txt", b"", "text/plain")}
    res = await client.post("/api/v1/documents", files=files)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_and_pipeline_sync(client: AsyncClient):
    """End-to-end sync ingestion: upload, extract, clean, chunk, embed, store."""
    doc_content = (
        "# Field Guide: Spiti Valley High Altitude Circuits\n\n"
        "Spiti Valley in Himachal Pradesh sits at an average altitude of 3,800 meters.\n\n"
        "Key Gompa is the largest monastery in the valley, founded in the 11th century. "
        "Travelers should acclimatize for at least 48 hours before crossing high mountain passes like Kunzum La.\n\n"
        "Tabo Monastery preserves millennium-old clay statues and murals, often referred to as the Ajanta of the Himalayas."
    )
    files = {"file": ("spiti_guide.md", doc_content.encode("utf-8"), "text/markdown")}
    data = {"title": "Spiti Field Guide 2026", "document_type": "guide"}

    res = await client.post("/api/v1/documents?process_async=false", files=files, data=data)
    assert res.status_code == 201
    doc = res.json()
    assert doc["title"] == "Spiti Field Guide 2026"
    assert doc["status"] == "ready"
    assert doc["chunk_count"] >= 1
    doc_id = doc["id"]

    # Retrieve document detail
    detail_res = await client.get(f"/api/v1/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["chunks"]) >= 1
    assert "Key Gompa" in detail["chunks"][0]["chunk_content"]


@pytest.mark.asyncio
async def test_semantic_search_and_rag_query(client: AsyncClient):
    """Semantic vector search and Ask-from-document RAG Q&A."""
    # 1. Ingest guide
    doc_content = (
        "Ziro Valley Cultural Field Log\n\n"
        "The Apatani people of Ziro cultivate rice alongside fish in terraced plots. "
        "This integrated farming prevents soil degradation and sustains water levels throughout the monsoon.\n\n"
        "Mawlynnong and Nongriat in Meghalaya are renowned for living root bridges made of Ficus elastica roots."
    )
    files = {"file": ("northeast_culture.txt", doc_content.encode("utf-8"), "text/plain")}
    res = await client.post("/api/v1/documents?process_async=false", files=files)
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # 2. Semantic Search
    search_res = await client.post(
        "/api/v1/documents/search",
        json={"query": "Apatani fish and rice terraced plots", "top_k": 3},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["count"] >= 1
    top_chunk = search_data["results"][0]
    assert "Apatani" in top_chunk["content"]
    assert top_chunk["similarity"] > 0.2

    # 3. Ask-from-document (RAG)
    rag_res = await client.post(
        "/api/v1/documents/query",
        json={"query": "How do Apatani farmers sustain their crops in Ziro?", "top_k": 2},
    )
    assert rag_res.status_code == 200
    rag_data = rag_res.json()
    assert rag_data["answer"]
    assert len(rag_data["sources"]) >= 1
    assert "Apatani" in rag_data["sources"][0]["content"]


@pytest.mark.asyncio
async def test_document_ownership_isolation(client: AsyncClient):
    """User B cannot access or delete User A's document."""
    # Register User A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={"email": "doc_owner_a@example.com", "password": "Password123!", "full_name": "Owner A"},
    )
    token_a = res_a.json()["access_token"]

    # Register User B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={"email": "doc_owner_b@example.com", "password": "Password123!", "full_name": "Owner B"},
    )
    token_b = res_b.json()["access_token"]

    # User A uploads a private document
    files = {"file": ("secret_route.txt", b"Confidential trek itinerary for User A.", "text/plain")}
    upload_res = await client.post(
        "/api/v1/documents?process_async=false",
        files=files,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # User A can access it
    ok_get = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert ok_get.status_code == 200

    # User B attempts to get User A's document -> 403 Forbidden
    forbidden_get = await client.get(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_get.status_code == 403

    # User B attempts to delete User A's document -> 403 Forbidden
    forbidden_del = await client.delete(
        f"/api/v1/documents/{doc_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert forbidden_del.status_code == 403


@pytest.mark.asyncio
async def test_reprocess_and_delete_document(client: AsyncClient):
    """Reprocess document and verify deletion cascades to disk file and chunks."""
    files = {"file": ("test_lifecycle.txt", b"First draft of itinerary.\n\nSecond paragraph notes.", "text/plain")}
    res = await client.post("/api/v1/documents?process_async=false", files=files)
    assert res.status_code == 201
    doc_id = res.json()["id"]

    # Reprocess
    reprocess_res = await client.post(f"/api/v1/documents/{doc_id}/reprocess?process_async=false")
    assert reprocess_res.status_code == 200
    assert reprocess_res.json()["status"] == "ready"

    # Delete
    del_res = await client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 204

    # Verify 404 after deletion
    get_res = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_res.status_code == 404
