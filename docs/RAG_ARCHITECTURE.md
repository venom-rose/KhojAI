# KHOJAI Document Ingestion & RAG Pipeline Architecture

## Overview
This document specifies the end-to-end Document Ingestion and Retrieval-Augmented Generation (RAG) pipeline built for **KHOJAI**. The architecture powers verified knowledge bases (travel advisories, regional field guides, homestay registries, offbeat route notes, and community contributions), enabling travelers and curators to upload travel resources and query them conversationally with source attribution.

---

## 1. Frontend Audit & Ingestion Specifications

An inspection of the KHOJAI frontend (`client/src/`) and data contracts established the requirements for document ingestion and retrieval:

| Component / Feature | Frontend & Backend Specification |
| :--- | :--- |
| **File Upload** | Secure multipart form upload (`POST /api/v1/documents`) with client-side filename preservation, sanitization, and progress monitoring. |
| **Document Library** | Paginated listing (`GET /api/v1/documents`) filtered by owner, status (`uploaded`, `processing`, `ready`, `failed`), and title search. |
| **Document Cards** | Serialized `DocumentOut` objects providing title, document type, file size, MIME type, chunk count, processing status, and timestamp metadata. |
| **Document Deletion** | `DELETE /api/v1/documents/{id}` with cascading deletion of database records, vector chunks, and physical files on disk (`HTTP 204`). |
| **Document Status** | Explicit lifecycle states: `uploaded` → `processing` → `ready` (or `failed` with recorded `error_message`). |
| **Search** | Semantic cosine similarity vector search (`POST /api/v1/documents/search`) returning matching chunks with similarity scores. |
| **Ask-from-Document** | RAG Question Answering (`POST /api/v1/documents/query` and `POST /api/v1/documents/{id}/query`) returning grounded LLM answers citing source chunks. |
| **Supported File Types** | `.pdf` (PDF documents), `.txt` (plain text), `.md` (Markdown field notes), `.json` (structured travel data), `.csv` (tabular routes and homestay tariffs). |
| **Upload Progress & Large Files** | Background execution via FastAPI `BackgroundTasks` for asynchronous extraction and embedding (`?process_async=true`). |
| **Document Metadata** | Stores word counts, line counts, page counts, chunk distributions, detected MIME types, and destination linkages. |

---

## 2. Ingestion & RAG Pipeline Flow

The pipeline executes a deterministic 12-stage lifecycle:

```
Upload (multipart stream)
   ↓
Validate (MIME, extension, size limit, non-empty)
   ↓
Store (unique non-executable doc_<uuid>.dat outside web root)
   ↓
Extract (PDF text via pypdf, Markdown, CSV, JSON)
   ↓
Clean (NFKC normalization, control char removal, whitespace collapsing)
   ↓
Chunk (Sliding window respecting paragraph & sentence boundaries)
   ↓
Embed (Local deterministic, Gemini text-embedding-004, or OpenAI)
   ↓
Store Vectors (DocumentChunk records with embedding vectors and metadata)
   ↓
Retrieve (Cosine similarity vector search with user ownership scoping)
   ↓
Build Context (Formatted citation blocks with document attribution)
   ↓
LLM Synthesis (Grounded answering via active AIProvider)
   ↓
Response (Answer text, citations, source chunks, token metrics)
```

---

## 3. Security Architecture & Threat Mitigations

1. **Path Traversal Prevention**:
   - Client-supplied filenames are never trusted as paths.
   - `sanitize_filename()` strips all path separators (`/`, `\`, `..`), null bytes (`\x00`), and control characters.
   - `validate_file_safety()` ensures target file paths resolve strictly within the designated storage directory (`os.path.commonpath`).
2. **Non-Executable Storage**:
   - Files are stored in `./media/documents/` using random UUID filenames (`doc_<uuid>.dat`).
   - The storage directory contains no execution permissions and is located completely outside web application document roots.
3. **Execution Prevention**:
   - Uploaded files are strictly parsed as passive text or binary data streams. No shell commands, interpreters, or native code execution are ever invoked on uploaded files.
4. **Document Ownership & Multi-Tenant Isolation**:
   - Every uploaded document is associated with the uploading user (`Document.user_id`).
   - Cross-user retrieval, deletion, or viewing attempts return `403 Forbidden`.
   - Semantic retrieval is scoped strictly to the requesting user's documents plus verified public system documents.
5. **Denial-of-Service (DoS) Protection**:
   - File uploads are checked during streaming read against `MAX_UPLOAD_SIZE_MB` (default 5MB), terminating immediately with `413 Payload Too Large`.
   - Empty files (0 bytes) are rejected with `400 Bad Request`.

---

## 4. Extraction, Cleaning, and Chunking

### 4.1. Extraction (`DocumentExtractor`)
- **PDF**: Uses `pypdf.PdfReader` to extract text page by page, tracking `page_count` and `extracted_pages`.
- **Markdown / Plain Text**: UTF-8 stream reader with automatic fallback to Latin-1 decoding.
- **CSV**: Structured tabular parser extracting column headers and row key-value pairs formatted for LLM comprehension.
- **JSON**: Formatted JSON structure parser preserving hierarchy and metadata.

### 4.2. Cleaning (`TextCleaner`)
- Unicode NFKC normalization.
- Control character and null byte stripping (`\x00-\x1f\x7f-\x9f`), preserving line breaks and tabs.
- Line-ending standardization (Windows `\r\n` and classic Mac `\r` converted to Unix `\n`).
- Consecutive blank line collapsing (maximum 2 blank lines).

### 4.3. Chunking (`TextChunker`)
- Sliding-window chunker with configurable `chunk_size` (750 chars) and `chunk_overlap` (120 chars).
- Preserves paragraph boundaries (`\n\n`) and sentence terminators (`.`, `?`, `!`).
- Attaches `chunk_index`, character length, word count, and estimated token counts to every chunk.

---

## 5. Embeddings & Vector Storage

### 5.1. Pluggable Embedding Architecture
The system defines a unified interface (`BaseEmbeddingProvider`) in `backend/app/rag/embeddings.py`:

```
BaseEmbeddingProvider
├── LocalEmbeddingProvider   (Deterministic offline hashed n-grams + L2 normalization)
├── GeminiEmbeddingProvider  (Google text-embedding-004 via REST HTTPX)
└── OpenAIEmbeddingProvider  (OpenAI text-embedding-3-small via REST HTTPX)
```

- **Local Provider**: Fast, zero-dependency, deterministic 256-dimensional embeddings for offline development, air-gapped environments, and CI testing.
- **Gemini / OpenAI Providers**: Cloud embedding models configured via `EMBEDDING_PROVIDER` and corresponding API keys.

### 5.2. Vector Storage & Semantic Search
- Stored directly in `document_chunks.embedding` as JSON float arrays.
- Cosine similarity calculation:
  $$\text{sim}(u, v) = \frac{u \cdot v}{\|u\|_2 \|v\|_2}$$
- Fully compatible with SQLite, asyncpg, and PostgreSQL with zero required external native binary extensions.

---

## 6. Endpoints Reference

Base URL: `/api/v1/documents`

### 6.1. Upload Document
- **POST** `/api/v1/documents`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: Binary file (`.txt`, `.md`, `.pdf`, `.csv`, `.json`)
  - `title`: Optional custom title (string)
  - `document_type`: `guide` | `advisory` | `field_note` | `itinerary` | `report`
  - `destination_id`: Optional UUID
  - `process_async`: `true` | `false` (default: `false`)
- **Status**: `201 Created`

### 6.2. List Documents
- **GET** `/api/v1/documents`
- **Query**: `limit`, `offset`, `status`, `search`
- **Status**: `200 OK`

### 6.3. Get Document Details
- **GET** `/api/v1/documents/{id}`
- **Response**: `DocumentDetailOut` with raw extracted text and all child `chunks`.
- **Status**: `200 OK`

### 6.4. Delete Document
- **DELETE** `/api/v1/documents/{id}`
- **Behavior**: Deletes document, cascaded chunks, and physical disk file.
- **Status**: `204 No Content`

### 6.5. Reprocess Document
- **POST** `/api/v1/documents/{id}/reprocess`
- **Behavior**: Clears old chunks and re-executes extraction, chunking, and embedding.
- **Status**: `200 OK`

### 6.6. Semantic Vector Search
- **POST** `/api/v1/documents/search`
- **Payload**:
```json
{
  "query": "Apatani fish and rice terraced plots in Ziro",
  "top_k": 4,
  "min_similarity": 0.1
}
```
- **Response**:
```json
{
  "query": "Apatani fish and rice terraced plots in Ziro",
  "results": [
    {
      "chunk_id": "8fa2...",
      "document_id": "c1f7...",
      "document_title": "Ziro Valley Cultural Field Log",
      "content": "The Apatani people of Ziro cultivate rice alongside fish in terraced plots...",
      "similarity": 0.8421,
      "metadata": { "chunk_index": 0, "word_count": 28 }
    }
  ],
  "count": 1
}
```

### 6.7. Ask-from-Document (RAG)
- **POST** `/api/v1/documents/query`
- **Payload**:
```json
{
  "query": "How do Apatani farmers sustain their crops in Ziro?",
  "top_k": 3
}
```
- **Response**:
```json
{
  "query": "How do Apatani farmers sustain their crops in Ziro?",
  "answer": "Apatani farmers practice a sustainable integrated paddy-cum-fish cultivation system...",
  "model": "khojai-local-v1",
  "sources": [ ... ],
  "token_count": 64
}
```

---

## 7. Verification & Automated Test Coverage

The RAG pipeline is validated by 10 dedicated automated tests in `backend/tests/test_rag.py` (part of the 46 passing tests across the backend):

1. `test_sanitize_filename_and_safety`: Path traversal prevention and filename cleaning.
2. `test_text_cleaner`: Unicode normalization, null byte removal, and whitespace control.
3. `test_text_chunker`: Paragraph and sentence boundary splitting with overlap.
4. `test_embedding_and_cosine_similarity`: Vector generation and semantic similarity.
5. `test_upload_unsupported_file_type`: Rejecting executable or unauthorized files (`HTTP 400`).
6. `test_upload_empty_file`: Rejecting 0-byte files (`HTTP 400`).
7. `test_upload_and_pipeline_sync`: End-to-end sync ingestion and chunk persistence.
8. `test_semantic_search_and_rag_query`: Cosine vector retrieval and LLM context synthesis.
9. `test_document_ownership_isolation`: User isolation enforcement (`HTTP 403`).
10. `test_reprocess_and_delete_document`: Reprocessing and cascade deletion of files and chunks.
