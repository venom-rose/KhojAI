# KHOJAI AI Provider Abstraction Architecture

## Overview
This document specifies the unified, provider-independent Artificial Intelligence (AI) abstraction layer implemented for **KHOJAI**. The architecture encapsulates LLM text generation, Server-Sent Events (SSE) streaming, and dense vector embedding generation behind a uniform interface, decoupled from specific cloud vendors or external dependencies.

---

## 1. Frontend Audit & Model Customization

An audit of the KHOJAI frontend (`client/src/`) established the following AI interaction requirements:

- **AI Model Selection**: Supported across conversation initialization and individual message prompts via `model?: string` (e.g. `gemini-1.5-flash`, `gpt-4o-mini`, `khojai-local-v1`).
- **Personalized Travel Intelligence**: User profiles configure personalization settings (`ai_pace`: "unhurried" | "balanced" | "intense", and `ai_curiosity_level`: "high" | "moderate") that guide system prompts.
- **Provider Confidentiality**: The frontend interacts strictly with our backend API. Raw cloud vendor credentials, endpoints, or keys are never exposed to client bundles or network responses.

---

## 2. Provider-Independent Architecture (`services/ai/`)

The architecture establishes a uniform base contract located in `backend/app/services/ai/`:

```
                       BaseAIProvider
                             │
       ┌─────────────────────┼─────────────────────┬─────────────────────┐
       ▼                     ▼                     ▼                     ▼
 GeminiProvider        OpenAIProvider        LocalProvider         MockAIProvider
(Google Gemini REST)   (OpenAI REST)     (Offline Deterministic) (Fault Injection/CI)
```

### 2.1. The Unified Interface (`BaseAIProvider`)

Every provider implements three core asynchronous methods:

```python
class BaseAIProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AIResponse:
        """Generate a complete non-streaming AI response."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response tokens incrementally."""
        ...

    @abstractmethod
    async def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """Generate normalized vector embeddings for single or batch texts."""
        ...
```

---

## 3. Implementations

### 3.1. `LocalProvider` ([local.py](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/app/services/ai/local.py))
- **Environment**: Default offline provider for local development, CI testing, and air-gapped deployments.
- **Capabilities**:
  - Curated Indian offbeat knowledge base (Ziro Valley, Spiti, Meghalaya bio-architecture, quiet Kerala backwaters, budget planning).
  - Word-by-word streaming simulation.
  - Deterministic 256-dimensional vector embedding generation with n-gram hashing and L2 normalization.
- **Dependencies**: 0 external API calls or keys required.

### 3.2. `GeminiProvider` ([gemini.py](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/app/services/ai/gemini.py))
- **Environment**: Google Gemini REST API via `httpx.AsyncClient`.
- **Default Models**: `gemini-1.5-flash` for generation and `text-embedding-004` for embeddings.
- **Capabilities**: Complete generation, SSE streaming chunking, and batch embedding.

### 3.3. `OpenAIProvider` ([openai.py](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/app/services/ai/openai.py))
- **Environment**: OpenAI REST API via `httpx.AsyncClient`.
- **Default Models**: `gpt-4o-mini` for generation and `text-embedding-3-small` for embeddings.
- **Capabilities**: Complete chat completions, delta streaming, and vector embeddings.

### 3.4. `MockAIProvider` ([mock.py](file:///c:/Users/kundu/OneDrive/Documents/KhojAI/backend/app/services/ai/mock.py))
- **Environment**: Automated testing and CI fault injection.
- **Configurable Faults**:
  - `should_timeout=True` (simulates upstream gateway timeouts).
  - `should_fail_auth=True` (simulates invalid API keys).
  - `should_fail_rate_limit=True` (simulates 429 rate limit errors).
  - `fail_attempts=N` (simulates N transient failures followed by successful retry).

---

## 4. Resilience & Reliability

### 4.1. Timeout Handling
- Default timeout: **30.0 seconds** (configurable via `AI_TIMEOUT_SECONDS`).
- Requests exceeding the threshold raise `AIProviderTimeoutError`, caught by FastAPI's global exception handler to return a clean `HTTP 504 Gateway Timeout`.

### 4.2. Exponential Backoff Retry
- Upstream network errors, transient 503 (Service Unavailable), or 429 (Rate Limit) trigger automatic retries up to `AI_MAX_RETRIES` (default 3 attempts) with exponential backoff:
  $$\text{delay} = 1.0 \times 2^{\text{attempt}}$$

### 4.3. Credential & Stack Trace Sanitization
- Upstream error messages are scrubbed through regex sanitizers:
  - URLs containing `key=AIzaSy...` are replaced with `key=[REDACTED]`.
  - Headers containing `Authorization: Bearer sk-...` are replaced with `Bearer [REDACTED]`.
- Internal stack traces are logged on the server and never returned in HTTP JSON responses.

### 4.4. Consistent Exception Hierarchy

| Exception | Upstream Condition | HTTP Status | Response Payload |
| :--- | :--- | :--- | :--- |
| `AIProviderTimeoutError` | Timeout exceeded | `504 Gateway Timeout` | `{"error": "AI service error", "detail": "...", "provider": "..."}` |
| `AIProviderAuthError` | Invalid or missing API key | `502 Bad Gateway` | `{"error": "AI service error", "detail": "...", "provider": "..."}` |
| `AIProviderRateLimitError`| Upstream rate limit reached | `503 Service Unavailable` | `{"error": "AI service error", "detail": "...", "provider": "..."}` |
| `AIProviderError` | Generic upstream failure | `502 Bad Gateway` | `{"error": "AI service error", "detail": "...", "provider": "..."}` |

---

## 5. Switching Providers

Switching the active provider requires only modifying the `.env` configuration:

```bash
# Option 1: Local deterministic (Offline / Zero-cost)
AI_PROVIDER=local

# Option 2: Google Gemini
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_NAME=gemini-1.5-flash

# Option 3: OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL_NAME=gpt-4o-mini

# Option 4: Mock Provider for CI/Testing
AI_PROVIDER=mock
```

---

## 6. Automated Test Coverage

The abstraction layer is validated by 9 dedicated tests in `backend/tests/test_ai_provider.py` (part of 61 tests passing across the backend):

1. `test_local_provider_interface`: Validates `generate()`, `stream()`, and `embed()` on `LocalProvider`.
2. `test_mock_provider_success`: Validates generation and streaming on `MockAIProvider`.
3. `test_mock_provider_timeout_error`: Verifies timeout simulation and status 504.
4. `test_mock_provider_auth_error`: Verifies credential failure simulation and status 502.
5. `test_mock_provider_rate_limit_error`: Verifies upstream rate limit handling and status 503.
6. `test_mock_provider_retry_handling`: Verifies retry loop recovers after transient failures.
7. `test_credential_sanitization`: Verifies API keys and Bearer tokens are scrubbed from error output.
8. `test_provider_factory_resolution`: Verifies dynamic provider instantiation via `get_ai_provider()`.
9. `test_unconfigured_cloud_providers_fail_safely`: Verifies cloud providers raise clean `AIProviderAuthError` without unhandled crashes when keys are omitted.
