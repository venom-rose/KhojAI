# KHOJAI Search & Discovery Backend Architecture

## Overview
This document specifies the search and discovery backend architecture implemented for **KHOJAI**. The search engine powers the faceted discovery interface (`/discover`), global command-palette search, hybrid document retrieval, and private conversation search with rate limiting and strict user isolation.

---

## 1. Frontend Search Interface Audit

An inspection of the KHOJAI frontend search interfaces (`client/src/pages/Discover.tsx` and `client/src/components/ui/command.tsx`) determined the specific search requirements:

| Capability | Frontend Requirement & Backend Specification |
| :--- | :--- |
| **Global Omnisearch** | `GET /api/v1/search?q=...` — Unified cross-entity search aggregating destinations, knowledge documents, and private conversations. |
| **Destination Faceted Search** | `GET /api/v1/search/destinations` — Matches the Discover page UI with search query and 6 refinement filters (`region`, `state`, `budget`, `style`, `season`, `experience`). |
| **Sorting** | Supports `Recommended`, `Most Trusted` (trust score desc), `Recently Updated` (updated_at desc), `Budget Friendly` (budget length asc), and `Offbeat`. |
| **Hybrid Document Search** | `GET /api/v1/search/documents?q=...` — Combines text keyword matching with semantic vector cosine similarity for rich document retrieval. |
| **Conversation Search** | `GET /api/v1/search/conversations?q=...` — Searches conversation titles, summaries, and dialogue message content with matched snippet extraction. |
| **Ownership Isolation** | Private conversations and user-uploaded documents are strictly isolated (`403` / omitted from search results for other users). |
| **Pagination** | All endpoints support standard pagination (`limit`, `offset`, `total`). |
| **Rate Limiting** | Sliding-window in-memory rate limiter (60 requests/minute per client) returning `429 Too Many Requests` with `Retry-After`. |

---

## 2. Hybrid Search Architecture

For document search, KHOJAI combines **Keyword Search** (exact, prefix, and token overlap matching) with **Semantic Vector Search** (dense embedding cosine similarity):

$$\text{Score}_{\text{hybrid}} = 0.5 \cdot \text{Score}_{\text{keyword}} + 0.5 \cdot \text{Similarity}_{\text{vector}}$$

```
                       User Search Query
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       Keyword Matcher                 Vector Embedder
   (SQL ILIKE + Token Overlap)       (Dense 256/768-d Vector)
               │                               │
               ▼                               ▼
         Keyword Score                 Cosine Similarity
               │                               │
               └───────────────┬───────────────┘
                               ▼
                    Hybrid Score Normalizer
                               │
                               ▼
                     Ranked Search Results
```

### Benefits:
- **Exact Token Matches**: Queries with specific entity names (e.g., "Tabo Monastery", "Apatani", "Kunzum Pass") receive high keyword confidence.
- **Conceptual Queries**: Queries with thematic wording (e.g., "high-altitude monasteries", "sustainable farming in hills") are retrieved via semantic vector proximity even without exact word overlap.

---

## 3. Endpoints Reference

Base URL: `/api/v1/search`
All search endpoints are protected by the sliding-window rate limiter dependency.

### 3.1. Global Omnisearch
- **GET** `/api/v1/search`
- **Parameters**:
  - `q`: Search string (required, 1–200 characters)
  - `limit`: Max results per category (default: 5, max: 20)
- **Response**: `GlobalSearchOut`
```json
{
  "query": "Ziro",
  "destinations": [
    {
      "id": "c1f7...",
      "slug": "ziro",
      "name": "Ziro Valley",
      "state": "Arunachal Pradesh",
      "region": "Northeast",
      "category": "Nature · Culture",
      "best_season": "Oct – Nov",
      "budget": "₹₹",
      "trust_score": 94,
      "description": "A peaceful high-altitude plateau...",
      "image_url": "https://...",
      "relevance_score": 1.0
    }
  ],
  "documents": [
    {
      "chunk_id": "8fa2...",
      "document_id": "9b1c...",
      "document_title": "Ziro Valley Cultural Field Log",
      "document_type": "guide",
      "content": "The Apatani people of Ziro cultivate rice alongside fish...",
      "similarity": 0.8124,
      "relevance_score": 0.8562
    }
  ],
  "conversations": [
    {
      "conversation_id": "7fa8...",
      "title": "Weekend in Ziro Valley",
      "summary": null,
      "matched_message": "What homestays would you recommend in Hong village?",
      "relevance_score": 1.0,
      "updated_at": "2026-09-05T17:15:00Z"
    }
  ],
  "total_hits": 3
}
```

---

### 3.2. Faceted Destination Search
- **GET** `/api/v1/search/destinations`
- **Parameters**:
  - `q`: Optional keyword
  - `region`: e.g. `Northeast`, `Himalayas`, `Western Ghats`
  - `state`: e.g. `Arunachal Pradesh`, `Himachal Pradesh`
  - `budget`: `₹`, `₹₹`, `₹₹₹`
  - `style`: `Slow travel`, `Outdoors`, `Culture-led`, `Road trip`
  - `season`: `Oct – Feb`, `Mar – Jun`, `Jun – Sep`, `Oct – Nov`, `Nov – Feb`
  - `experience`: `Nature`, `Culture`, `Food`, `Outdoors`, `Heritage`
  - `sort`: `Recommended`, `Most Trusted`, `Recently Updated`, `Budget Friendly`, `Offbeat`
  - `limit`: int (default: 20)
  - `offset`: int (default: 0)
- **Response**: `PaginatedDestinationSearchOut`

---

### 3.3. Hybrid Document Search
- **GET** `/api/v1/search/documents`
- **Parameters**:
  - `q`: Search inquiry (required)
  - `document_type`: Optional category filter
  - `min_similarity`: Cutoff threshold (default: 0.0)
  - `limit`: int (default: 10)
  - `offset`: int (default: 0)
- **Response**: `PaginatedDocumentSearchOut` (ranked by hybrid relevance).

---

### 3.4. Conversation History Search
- **GET** `/api/v1/search/conversations`
- **Parameters**:
  - `q`: Search inquiry (required)
  - `is_pinned`: Optional boolean
  - `is_archived`: Optional boolean
  - `limit`: int (default: 10)
  - `offset`: int (default: 0)
- **Response**: `PaginatedConversationSearchOut` (scoped to authenticated user).

---

## 4. Rate Limiting & Protection

- **Implementation**: Sliding-window rate limiter ([rate_limiter.py](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/app/security/rate_limiter.py)) tracking timestamp windows per client IP / Authorization token.
- **Threshold**: 60 requests per 60-second window.
- **Excess Handling**: Returns `HTTP 429 Too Many Requests` with `Retry-After: <seconds>` header.

---

## 5. Automated Test Coverage

The search engine is verified across 6 dedicated test cases in `backend/tests/test_search.py`:
1. `test_search_rate_limiter_logic`: Verifies 429 response when request limits are exceeded.
2. `test_destination_search_keyword_and_filters`: Validates keyword matching, regional filters, budget filters, and sorting.
3. `test_hybrid_document_search`: Validates combined text match and vector similarity scoring.
4. `test_conversation_search_and_isolation`: Verifies that User A's dialogue snippets are searchable by User A, but return 0 hits for User B.
5. `test_global_omnisearch`: Validates cross-entity aggregation across destinations, documents, and threads.
6. `test_search_validation_errors`: Validates 422 responses on invalid search queries.
