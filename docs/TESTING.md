# KHOJAI Testing Guide & Test Suite Documentation

Comprehensive documentation for running all backend tests, security verification, frontend checks, and end-to-end user flows in the KHOJAI platform.

---

## 1. Test Suite Architecture

The KHOJAI testing infrastructure spans **81 automated backend tests** and full-stack browser-driven E2E tests:

| Test Module | Coverage Scope | Tests |
| :--- | :--- | :---: |
| [`test_e2e_16_flows.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_e2e_16_flows.py) | Full 16-step user journey from registration to cleanup | 1 |
| [`test_e2e_comprehensive.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_e2e_comprehensive.py) | Negative testing, expired auth, oversized uploads, 400/401/403/404/413/422 status codes | 13 |
| [`test_security_audit.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_security_audit.py) | Cross-user isolation, prompt injection fences, header auth, security response headers | 6 |
| [`test_auth.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_auth.py) | Registration, duplicate checks, login, refresh tokens, logout session revocation | 10 |
| [`test_chat.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_chat.py) | Conversations, messages, AI response persistence, SSE streaming, regeneration | 11 |
| [`test_rag.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_rag.py) | Text extraction, cleaning, chunking, vector similarity, Ask-from-document | 10 |
| [`test_search.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_search.py) | Omnisearch, semantic document search, conversation search, ranking, filters | 6 |
| [`test_ai_provider.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_ai_provider.py) | AI abstraction (Local, Gemini, OpenAI), fallback handling, retry mechanisms | 9 |
| [`test_users.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_users.py) | Profile updates, AI preferences, password changes, account soft deletion | 7 |
| [`test_database.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_database.py) | Foreign keys, cascading deletion, indexes, ORM relationships, migrations | 8 |

---

## 2. Prerequisites & Environment Setup

### System Requirements
* **Python**: 3.11+ (Python 3.14 recommended)
* **Node.js**: 20+
* **Package Manager**: `pnpm` (managed via `corepack pnpm`)

### Setup Environment
1. **Activate Python Virtual Environment**:
   ```powershell
   # Windows PowerShell
   .\backend\venv\Scripts\Activate.ps1
   ```

2. **Initialize Local Database**:
   ```powershell
   .\backend\venv\Scripts\python.exe backend/init_db.py
   ```

3. **Install Frontend Dependencies**:
   ```powershell
   corepack pnpm install
   ```

---

## 3. Running Backend Tests

All automated backend tests run with in-memory isolation (`sqlite+aiosqlite:///:memory:`) and mocked/local AI providers, requiring no external network connectivity or paid API keys.

### Run All 81 Backend Tests
```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

### Run the 16 Primary User Flows
```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_e2e_16_flows.py -v
```

### Run Comprehensive E2E & Error Code Suite
```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_e2e_comprehensive.py -v
```

### Run Security & Multi-Tenancy Tests
```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_security_audit.py -v
```

### Run Specific Functional Areas
```powershell
# Authentication & Tokens
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_auth.py -v

# Conversations & Messaging
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_chat.py -v

# Document Ingestion & RAG
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_rag.py -v

# Search & Retrieval
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_search.py -v

# AI Provider Abstraction
.\backend\venv\Scripts\python.exe -m pytest backend/tests/test_ai_provider.py -v
```

---

## 4. Running Frontend Verification

### TypeScript Typechecking
Verify there are no missing types or interface mismatches:
```powershell
corepack pnpm check
```

### Production Bundle Build
Test bundle compilation via Vite and esbuild:
```powershell
corepack pnpm run build
```

---

## 5. Running the Complete Local Full-Stack Application

To test the frontend against the live backend locally:

### Terminal 1: Launch FastAPI Backend
```powershell
.\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
* Backend API documentation: `http://127.0.0.1:8000/docs`
* Backend OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
* Backend Health Check: `http://127.0.0.1:8000/api/v1/health`

### Terminal 2: Launch Vite Frontend Dev Server
```powershell
corepack pnpm run dev
```
* Application accessible at: `http://localhost:3000/`
* Requests to `/api/*` are automatically proxied by Vite to `http://127.0.0.1:8000`.

---

## 6. Matrix of 16 Verified End-to-End User Flows

The test file [`test_e2e_16_flows.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_e2e_16_flows.py) and the browser test suite validate the following flows:

| Step | Flow Description | API Endpoint / UI Action | Expected Result |
| :---: | :--- | :--- | :--- |
| **1** | **Register** | `POST /api/v1/auth/register` | 201 Created, JWT access token returned |
| **2** | **Login** | `POST /api/v1/auth/login` | 200 OK, session cookie set, user profile returned |
| **3** | **Logout** | `POST /api/v1/auth/logout` | 200 OK, session revoked, cookie cleared |
| **4** | **Create Conversation** | `POST /api/v1/chat/conversations` | 201 Created with conversation ID and title |
| **5** | **Send Message** | `POST /api/v1/chat/conversations/{id}/messages` | 200 OK, user message stored |
| **6** | **Receive AI Response** | AI Provider (Local/Gemini) | Assistant response generated and persisted |
| **7** | **Refresh Page** | `GET /api/v1/chat/conversations/{id}` | 200 OK, conversation state retrieved |
| **8** | **Conversation Remains Available** | `GET /api/v1/chat/conversations/{id}/messages` | Both user prompt and assistant response persist |
| **9** | **Upload Document** | `POST /api/v1/documents` | 201 Created, unique non-executable storage ID |
| **10** | **Document Processing** | Ingestion pipeline | Status reaches `ready`, chunks and vectors created |
| **11** | **Search Document** | `GET /api/v1/search/documents?q=...` | 200 OK, hybrid matches with similarity scores |
| **12** | **Ask Question About Document** | `POST /api/v1/documents/query` | 200 OK, vector retrieval selects top-k chunks |
| **13** | **Receive Context-Aware Answer** | RAG generation pipeline | AI answer generated citing document source chunks |
| **14** | **Delete Document** | `DELETE /api/v1/documents/{id}` | 204 No Content, chunks and files removed |
| **15** | **Delete Conversation** | `DELETE /api/v1/chat/conversations/{id}` | 204 No Content, conversation and messages purged |
| **16** | **Edit Profile / Settings** | `PATCH /api/v1/users/me` & `preferences` | 200 OK, theme, bio, and AI styles updated |

---

## 7. HTTP Error Code Verification Matrix

Tested in [`test_e2e_comprehensive.py`](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/tests/test_e2e_comprehensive.py):

* **400 Bad Request**: Unsupported file type (`.exe`, `.py`), empty 0-byte upload.
* **401 Unauthorized**: Expired access token, malformed signature, missing authorization credentials.
* **403 Forbidden**: Cross-tenant resource access (User B accessing User A's private threads/documents), deactivated account access.
* **404 Not Found**: Querying or deleting non-existent conversation or document UUIDs.
* **409 Conflict**: Duplicate registration with an existing email address.
* **413 Request Entity Too Large**: File uploads exceeding configured `MAX_UPLOAD_SIZE_MB`.
* **422 Unprocessable Entity**: Invalid or empty search queries (`min_length=1`), malformed JSON payloads.
