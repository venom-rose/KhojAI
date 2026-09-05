# KhojAI Frontend-Backend Integration Report

## 1. Overview

This document describes the full integration of the **KhojAI** FastAPI/PostgreSQL/AI backend with the existing Manus-generated frontend application.

The integration strictly preserves the existing design language, typography (font-display, font-mono), custom color palette (`#1a1f17` ink, `#c5653a` saffron, `#5d6b43` olive, `#f4f5f0` paper), layout structure, and animations without redesigning or replacing the frontend framework.

---

## 2. Architecture & Service Layer

All frontend components communicate with the backend through a centralized, resilient service layer located in `client/src/services/`. Direct, ad-hoc `fetch()` calls have been eliminated in favor of typed service contracts and interceptors.

```
client/src/
├── services/
│   ├── apiClient.ts      # Centralized Axios client, interceptors, auth token management
│   ├── auth.ts           # Authentication (login, register, me, logout, refresh)
│   ├── chat.ts           # Conversations, messages, SSE token streaming, regeneration
│   ├── documents.ts      # File upload with progress, list, chunk inspect, ask-document Q&A
│   ├── search.ts         # Omnisearch (destinations, documents, conversations)
│   └── users.ts          # User profile, preferences, deletion
├── contexts/
│   └── AuthContext.tsx   # React context for user state, session tracking, expiration handling
└── components/
    ├── AuthModal.tsx          # Login & Register modal dialog with validation
    ├── ChatModal.tsx          # Travel AI copilot slide-over with SSE streaming & model selector
    ├── DocumentModal.tsx      # RAG Vault: file dropzone, upload progress, chunk status, Q&A
    └── GlobalSearchDialog.tsx # Cmd+K universal search across destinations, docs, and chat
```

### Centralized API Client (`client/src/services/apiClient.ts`)
- **Base URL Resolution:**
  ```ts
  export const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.NEXT_PUBLIC_API_BASE_URL ||
    "/api/v1";
  ```
- **Vite Proxy Config:** Configured in `vite.config.ts` to forward `/api` requests to `http://127.0.0.1:8000`.
- **Bearer Token Interceptor:** Automatically injects the stored JWT token into all outgoing requests.
- **Session Expiration Interceptor:** On receiving HTTP `401 Unauthorized`, clears local tokens and broadcasts `khojai:auth_expired` event to trigger user re-authentication gracefully.
- **Error Formatting:** Centralized `extractErrorMessage()` translates FastAPI Pydantic validation errors (`detail` strings and objects) into user-friendly notifications.

---

## 3. Connected Features & Workflows

### A. Authentication System (`services/auth.ts`, `AuthContext.tsx`, `AuthModal.tsx`)
- **Login:** Connects to `POST /api/v1/auth/login` (OAuth2 password form request). Stores JWT and hydrates user state.
- **Registration:** Connects to `POST /api/v1/auth/register`. Validates email, password strength, and optional full name.
- **Current User:** Automatically verifies session on mount via `GET /api/v1/auth/me`.
- **Logout:** Connects to `POST /api/v1/auth/logout`, cleans local storage, and resets UI state.
- **Header State:** `SiteHeader` displays active user initial badge, first name, and sign-out action when logged in; renders "Sign In" when anonymous.

### B. Intelligent Chat & Travel Copilot (`services/chat.ts`, `ChatModal.tsx`)
- **Conversation Management:** Lists past threads via `GET /api/v1/chat/conversations`, creates new threads, loads messages via `GET /api/v1/chat/conversations/{id}/messages`.
- **Real-Time Token Streaming:** Implements Server-Sent Events (SSE) streaming via `chatService.streamMessage()` targeting `POST /api/v1/chat/conversations/{id}/messages/stream`. Smooth typing/token emission.
- **AI Model Selection:** Toggle between `khojai-local-v1`, `gemini-1.5-flash`, and `gpt-4o-mini`.
- **Regenerate & Delete:** Full support for regenerating the last assistant response or pruning threads.
- **Trigger:** Accessible via the "AI Copilot" header pill or the floating "Ask KhojAI" badge in the bottom-right of every page.

### C. RAG Knowledge Vault & Document Q&A (`services/documents.ts`, `DocumentModal.tsx`)
- **Drag & Drop Upload:** Accepts `.pdf`, `.txt`, `.md`, `.csv`, `.json` up to 20MB.
- **Upload Progress Bar:** Tracks chunking and transmission via Axios `onUploadProgress`.
- **Status Badges:** Real-time feedback showing `ready` (Indexed with chunk count), `processing`, or `failed`.
- **Ask-from-Document:** Grounded question-answering with citation excerpts, similarity scores, and chunk indices.
- **Trigger:** Accessible via the "Vault" button in `SiteHeader`.

### D. Universal Omnisearch (`services/search.ts`, `GlobalSearchDialog.tsx`)
- **Shortcut:** Triggerable via `Cmd+K` / `Ctrl+K` or clicking "Search ⌘K" in the header.
- **Debounced Global Query:** Queries `GET /api/v1/search?q={query}` across curated destinations, uploaded field guides, and chat history.
- **Direct Navigation:** Click-through to destination detail pages, document inspect, or chat conversations.

### E. Destination Discovery (`pages/Discover.tsx`)
- **Backend Faceted Search:** Wired to `searchService.searchDestinations()`, filtering by region, state, budget, travel style, season, and experience tags.
- **Sorting:** Connected to `Recommended`, `Most Trusted`, `Budget Friendly`, `Offbeat`.
- **Loading & Empty State:** Displays animated loader during network fetches and a styled reset card when no matches are found.
- **Resilient Fallback:** Seamlessly degrades to local destination intelligence if the backend is unreachable.

### F. Community Field Log (`pages/Contribute.tsx`)
- **Field Note Ingestion:** Converts submitted place names, stories, and contributor names into structured Markdown field notes, indexing them directly into the RAG vector store (`documentService.uploadDocument`).
- **Attachment Support:** Allows uploading guidebooks, offline itineraries, or notes via the file picker.

---

## 4. Verification & Testing

1. **TypeScript Typecheck:**
   ```bash
   corepack pnpm check
   # > tsc --noEmit
   # Exited with code 0 (0 errors)
   ```
2. **Frontend Production Build:**
   ```bash
   corepack pnpm run build
   # ✓ 1651 modules transformed.
   # ../dist/public/index.html   367.66 kB
   # ../dist/public/assets/...   Built in 8.74s (Exited with code 0)
   ```
3. **Backend Automated Test Suite:**
   ```bash
   backend/venv/Scripts/python.exe -m pytest backend/tests/
   # ============================= 61 passed in 13.20s =============================
   # test_ai_provider.py ......... [14%]
   # test_auth.py ..........        [31%]
   # test_chat.py ...........       [49%]
   # test_database.py ........      [62%]
   # test_rag.py ..........         [78%]
   # test_search.py ......          [88%]
   # test_users.py .......          [100%]
   ```
