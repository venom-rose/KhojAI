# KHOJAI Chat & Travel Intelligence Backend API

## Overview
This document specifies the chat and travel intelligence backend architecture implemented for **KHOJAI**. It details the frontend inspection results, data models, pluggable AI provider abstraction, Server-Sent Events (SSE) streaming protocol, endpoints, and integration patterns.

---

## 1. Frontend Audit & Contract Specification

Inspection of the existing KHOJAI frontend (`client/src/`) revealed that the current production UI uses a structured 5-step trip planner (`/planner` & `/planner/results`) with an ethos articulated as:
> *"Not a chatbot. A considered starting point for a journey that fits your pace, budget and curiosity."*

To extend KHOJAI with rich conversational intelligence without breaking any existing UX, the backend establishes a versatile, production-ready Chat API designed to power conversational modals, itinerary copilots, floating guides, and dedicated thread views.

| Feature | Specification & Behavior |
| :--- | :--- |
| **Message Format** | UUID primary key, `conversation_id`, `sender_type` (`user`, `assistant`, `system`), `content` (Markdown/Text), `model_name`, `token_count`, `metadata_json` (citations, attachments, tips), `created_at`. |
| **Conversation Format** | UUID primary key, optional `user_id` (supports authenticated travelers and guest sessions), `title`, `summary`, `model`, `is_pinned`, `is_archived`, `message_count`, `created_at`, `updated_at`. |
| **Streaming Behavior** | Native Server-Sent Events (SSE) via `text/event-stream` (`POST .../messages?stream=true`). Emits `event: token`, `event: done`, and `event: error`. Non-streaming requests return standard JSON (`ChatMessageOut`). |
| **Model Selector** | Client can specify `model` per conversation or per message payload (`gemini-1.5-flash`, `gpt-4o-mini`, `khojai-local-v1`). Defaults to server configuration. |
| **Chat History** | Paginated listing (`GET /api/v1/chat/conversations`) ordered by pinned state and recency, and deep conversation loading with chronological messages (`GET /api/v1/chat/conversations/{id}`). |
| **Attachments** | Optional `attachments: [{type, url, name, size}]` payload in `MessageCreateIn`, persisted within `metadata_json`. |
| **Regenerate Functionality** | `POST /api/v1/chat/conversations/{id}/regenerate` (or for a specific message ID) regenerates the assistant response using previous dialogue context and replaces or updates the message. |
| **Delete Conversation** | `DELETE /api/v1/chat/conversations/{id}` permanently deletes the conversation and cascades to delete all child messages (`HTTP 204`). |
| **New Conversation** | `POST /api/v1/chat/conversations` with optional title and optional `initial_message` (automatically triggers initial user message and AI reply in one atomic transaction). |
| **Loading & Error States** | Real-time token streaming for progressive rendering. Structured JSON errors with standard HTTP status codes (`400`, `401`, `403`, `404`, `502`). |

---

## 2. Pluggable AI Provider Architecture

The backend implements an extensible object-oriented abstraction hierarchy allowing zero-downtime provider switching via environment variables:

```
AIProvider (BaseAIProvider)
├── GeminiProvider  (Google Gemini 1.5/2.0 REST API via HTTPX)
├── OpenAIProvider  (OpenAI GPT-4o/mini Chat Completions API via HTTPX)
└── LocalProvider   (Deterministic offline Indian travel intelligence)
```

### Provider Factory
Providers are resolved dynamically via `get_ai_provider()` in `backend/app/ai/factory.py`:
- **Configuration**: Set `AI_PROVIDER=local`, `AI_PROVIDER=gemini`, or `AI_PROVIDER=openai` in `.env`.
- **Zero API Key Leakage**: Keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `AI_API_KEY`) reside strictly on the backend server. The client only ever receives synthesized markdown text and metadata from KHOJAI endpoints.
- **Offline / CI Resilience**: `LocalProvider` requires no external internet connection or credentials, providing realistic, nuanced Indian travel advice (e.g. Ziro Valley, Spiti, Meghalaya living bridges) with word-by-word streaming simulation for offline development and CI test runners.

---

## 3. Endpoints Reference

Base URL: `/api/v1/chat`

### 3.1. Create Conversation
- **Route**: `POST /api/v1/chat/conversations`
- **Auth**: Optional (`Bearer <token>` or session cookie).
- **Status**: `201 Created`
- **Request Body**:
```json
{
  "title": "Weekend in Ziro Valley",
  "model": "khojai-local-v1",
  "initial_message": "What homestays would you recommend in Hong village?"
}
```
- **Response**: `ConversationDetailOut` (includes initialized conversation and initial messages if `initial_message` was provided).

---

### 3.2. List Conversations
- **Route**: `GET /api/v1/chat/conversations`
- **Auth**: Optional. Authenticated users see their own threads; guest sessions list unowned threads.
- **Query Parameters**:
  - `limit`: `int` (default: 20, max: 100)
  - `offset`: `int` (default: 0)
  - `search`: `string` (filter titles case-insensitively)
  - `include_archived`: `boolean` (default: `false`)
- **Status**: `200 OK`
- **Response**:
```json
{
  "items": [
    {
      "id": "7fa85b64-5717-4562-b3fc-2c963f66afa6",
      "user_id": "c1f76d28-89c0-4828-98e0-1c4b37f4ea69",
      "title": "Weekend in Ziro Valley",
      "summary": null,
      "model": "khojai-local-v1",
      "is_pinned": true,
      "is_archived": false,
      "message_count": 4,
      "created_at": "2026-09-05T17:00:00Z",
      "updated_at": "2026-09-05T17:15:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### 3.3. Get Conversation Details
- **Route**: `GET /api/v1/chat/conversations/{conversation_id}`
- **Auth**: Optional. If conversation has an owner, requester must match owner (`403 Forbidden` if unauthorized).
- **Status**: `200 OK`
- **Response**: `ConversationDetailOut` containing metadata and full chronological `messages: [...]`.

---

### 3.4. Update / Rename Conversation
- **Route**: `PATCH /api/v1/chat/conversations/{conversation_id}`
- **Status**: `200 OK`
- **Request Body**:
```json
{
  "title": "Autumn in Arunachal Pradesh",
  "is_pinned": true,
  "is_archived": false
}
```

---

### 3.5. Delete Conversation
- **Route**: `DELETE /api/v1/chat/conversations/{conversation_id}`
- **Status**: `204 No Content`
- **Behavior**: Cascades deletion to all child messages.

---

### 3.6. Send Message (Sync or Streaming)
- **Route**: `POST /api/v1/chat/conversations/{conversation_id}/messages`
- **Query Parameter**: `stream=true` (optional, or in JSON body)
- **Request Body**:
```json
{
  "content": "Are the roads to Tabo Monastery open in late October?",
  "model": "khojai-local-v1",
  "stream": true,
  "attachments": [
    {
      "type": "image",
      "url": "https://example.com/spiti-pass.jpg",
      "name": "pass_status.jpg"
    }
  ]
}
```

#### Synchronous Response (`stream=false`):
- Content-Type: `application/json`
- Returns: `ChatMessageOut` (assistant reply message)

#### Server-Sent Events Streaming (`stream=true`):
- Content-Type: `text/event-stream`
- Protocol stream events:
```
event: token
data: {"token": "Spiti ", "done": false}

event: token
data: {"token": "rewards ", "done": false}

event: done
data: {"message_id": "9a7f...", "content": "Full text...", "model": "khojai-local-v1", "done": true, "finish_reason": "stop"}
```

---

### 3.7. Regenerate Assistant Response
- **Route**: `POST /api/v1/chat/conversations/{conversation_id}/regenerate` (latest message)
- **Route**: `POST /api/v1/chat/conversations/{conversation_id}/messages/{message_id}/regenerate` (specific message)
- **Status**: `200 OK`
- **Request Body**:
```json
{
  "model": "gpt-4o-mini"
}
```
- **Response**: `ChatMessageOut` with updated content and `regenerated_at` timestamp metadata.

---

## 4. Frontend Integration Examples

### 4.1. Reading Streaming Responses (SSE with Fetch API)

```typescript
async function sendMessageStream(conversationId: string, text: string, onToken: (t: string) => void) {
  const response = await fetch(`/api/v1/chat/conversations/${conversationId}/messages?stream=true`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${accessToken}`, // Optional
    },
    body: JSON.stringify({ content: text, stream: true }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  if (!reader) return;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split("\n");

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const payload = JSON.parse(line.slice(6));
        if (payload.token) {
          onToken(payload.token);
        }
      }
    }
  }
}
```

---

## 5. Security & Isolation Guarantee
1. **User Isolation**: A conversation belonging to User A returns `403 Forbidden` if requested or modified by User B.
2. **Anonymous Fallback**: Guest sessions can create and explore conversations without requiring an upfront login, but can be securely linked when authenticated.
3. **No Key Exposure**: LLM API tokens never touch the client or transit through public headers.
4. **Input Constraints**: Messages validated via Pydantic (`min_length=1`, `max_length=20000`) preventing denial-of-service memory pressure.
