# KHOJAI Security Policy & Audit Specification

## 1. Security Policy & Vulnerability Disclosure

KhojAI is committed to ensuring the safety, privacy, and integrity of all user data and AI interactions. If you discover a potential security vulnerability, please report it privately:

- **Security Contact:** security@khojai.ai
- **Response SLA:** Initial acknowledgment within 24 hours; remediation within 72 hours for critical issues.
- **Responsible Disclosure:** Please do not disclose vulnerabilities publicly until remediation has been verified and released.

---

## 2. Threat Model & Security Architecture

### A. Authentication & Session Management
- **Password Hashing:** Passwords are never stored in plaintext. They are hashed using **bcrypt** with a work factor of 12 rounds and automated per-user salt generation.
- **Password Complexity Validation:** Enforced minimum 8 characters, maximum 128 characters, requiring at least one alphabetical letter and one numeric digit.
- **Access Tokens (JWT):** Signed using HMAC-SHA256 (`HS256`) with a cryptographically random secret (enforced ≥ 32 characters). Access tokens have a limited lifetime (30 minutes) containing minimal user metadata (`sub`, `email`, `role`).
- **Refresh & Session Tokens:** Cryptographically generated via `secrets.token_hex(32)`, stored in HTTP-only, SameSite cookies with automatic HTTPS enforcement in production environments.
- **Session Revocation:** Logout explicitly revokes active sessions in the database and expires client cookies.

### B. User Isolation & Access Control (RBAC & Multi-Tenancy)
KhojAI enforces **strict backend-level ownership validation**. A user can **never** access another user's data:

| Resource | Ownership Enforcement | Unauthenticated Access |
| :--- | :--- | :--- |
| **Conversations** | Verified via `conversation.user_id == current_user.id`. | Strictly limited to unassigned anonymous sessions; cannot read/modify authenticated user threads. |
| **Messages** | Inherited from conversation ownership validation. | Denied access to private threads. |
| **Documents** | Verified via `doc.user_id == current_user.id`. | Strictly limited to shared public reference documents (`user_id is None`). Private docs raise 403 Forbidden. |
| **Vector Embeddings** | Cosine similarity search scoped to `user_id == current_user.id` + public docs. | Only searches public documents. Cannot match private chunks. |
| **Search History** | Scoped strictly to `Conversation.user_id == current_user.id`. | Restricted to anonymous threads; never leaks other users' queries or titles. |
| **Profile Data** | Bound strictly to `current_user` derived from the validated JWT token (`/api/v1/users/me`). | 401 Unauthorized. |

### C. File Upload Security & RAG Ingestion Pipeline
- **Filename Sanitization:** All client-provided filenames are sanitized by stripping path traversal sequences (`..`, `/`, `\`), null bytes (`\x00`), and control characters via `sanitize_filename()`.
- **Storage Isolation:** Uploaded files are written with non-deterministic random storage names (e.g. `doc_<uuid>.dat`) to a dedicated non-executable media directory (`media/documents/`). Files are never executed on the host.
- **Path Traversal Guards:** `validate_file_safety()` resolves absolute canonical paths and verifies that file operations remain strictly within `MEDIA_DIR`.
- **MIME & Extension Whitelist:** Only `.pdf`, `.txt`, `.md`, `.csv`, and `.json` are accepted. Unsupported file types are rejected before storage.
- **File Size Caps:** Uploads are streamed in 64KB chunks with strict enforcement of maximum file size limits (default 20MB) to prevent disk exhaustion attacks.
- **Physical File Cleanup:** Deleting a document permanently removes its database record, chunk embeddings, and the physical disk file.

### D. AI & Prompt Injection Defenses
- **Server-Side Credential Containment:** AI provider keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`) reside exclusively in server-side environment variables and are never transmitted to the frontend.
- **Header-Based Authentication:** Outgoing calls to Gemini use `x-goog-api-key` in HTTP headers rather than URL query parameters, preventing credential exposure in proxy access logs.
- **Anti-Prompt-Injection Delimiters:** Ingestion content and user queries are encapsulated in explicit XML boundaries:
  - `<travel_knowledge_context>`
  - `<user_question>`
- **Defensive System Instructions:** AI system prompts instruct the model to treat all contextual evidence strictly as factual, untrusted data, and to ignore any instruction overrides embedded within document text.
- **Escaped Text Rendering:** React's standard JSX text interpolation is used for AI message rendering, ensuring content is treated as text rather than raw executable HTML (preventing XSS).

### E. Network, CORS & API Protection
- **CORS Whitelist:** Configured via `CORS_ORIGINS` to accept only authorized origins. Wildcard `*` origins with credentials are prohibited.
- **Security Headers:** FastAPI middleware injects:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (production)
- **Rate Limiting:** Sliding-window rate limiters protect search and retrieval endpoints against automated enumeration and Denial of Service.
- **SQL Injection Prevention:** All database operations use SQLAlchemy 2.0 ORM and parameterized async queries. Raw SQL string concatenation is prohibited.

---

## 3. Security Audit & Remediation Log

| ID | Category | Severity | Description | Status |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Authorization | **CRITICAL** | `get_conversation_or_404` bypassed ownership checks when caller was unauthenticated (`user_id is None`). | **FIXED** — Enforced 403 Forbidden on any unauthorized caller when `conv.user_id is not None`. |
| **SEC-02** | Information Disclosure | **CRITICAL** | `list_conversations` returned conversations across all users when called without an auth token. | **FIXED** — Restricted anonymous listings strictly to `Conversation.user_id.is_(None)`. |
| **SEC-03** | Authorization | **CRITICAL** | `get_document_or_404` and `delete_document` allowed unauthenticated access and deletion of private user documents. | **FIXED** — Enforced strict ownership validation requiring matching `user_id`. |
| **SEC-04** | Information Disclosure | **CRITICAL** | `list_documents` and `semantic_search` leaked private documents across users when unauthenticated. | **FIXED** — Scoped unauthenticated queries strictly to public system documents (`user_id is None`). |
| **SEC-05** | Information Disclosure | **CRITICAL** | Omnisearch and conversation search searched all users' private dialogue threads when unauthenticated. | **FIXED** — Enforced strict user scoping on `search_conversations` and `search_documents_hybrid`. |
| **SEC-06** | Credential Exposure | **HIGH** | Gemini provider passed API key in URL query parameter (`?key=...`), exposing it to URL access logs. | **FIXED** — Migrated to secure `x-goog-api-key` HTTP header. |
| **SEC-07** | Prompt Injection | **HIGH** | Document context was concatenated directly with user prompt without boundary tags or safety instructions. | **FIXED** — Added XML boundary tags, sanitized closing tags, and anti-override system prompt instructions. |
| **SEC-08** | Cryptography | **MEDIUM** | `JWT_SECRET` could allow insecure short keys in misconfigured environments. | **FIXED** — Added Pydantic field validator enforcing minimum 32 characters. |
| **SEC-09** | Network Security | **MEDIUM** | Missing standard security response headers (X-Frame-Options, X-Content-Type-Options, HSTS). | **FIXED** — Added SecurityHeaders middleware to FastAPI application. |
