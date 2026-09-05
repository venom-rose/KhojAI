import asyncio
import pytest
from httpx import AsyncClient

from backend.app.services.ai import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    BaseAIProvider,
    GeminiProvider,
    LocalProvider,
    MockAIProvider,
    OpenAIProvider,
    get_ai_provider,
)
from backend.app.services.ai.gemini import _sanitize_error_text as sanitize_gemini
from backend.app.services.ai.openai import _sanitize_error_text as sanitize_openai


@pytest.mark.asyncio
async def test_local_provider_interface():
    """Verify LocalProvider implements generate, stream, and embed."""
    provider = LocalProvider()

    # 1. generate()
    res = await provider.generate(
        messages=[{"role": "user", "content": "What is unique about Ziro Valley?"}]
    )
    assert res.content
    assert "Ziro" in res.content
    assert res.model_name
    assert "citations" in res.metadata

    # 2. stream()
    tokens = []
    async for t in provider.stream(
        messages=[{"role": "user", "content": "Spiti offbeat homestays"}]
    ):
        tokens.append(t)
    assert len(tokens) > 0
    assert "Spiti" in "".join(tokens)

    # 3. embed()
    vectors = await provider.embed(texts=["Ziro Valley Arunachal", "High altitude Spiti"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 256
    assert len(vectors[1]) == 256


@pytest.mark.asyncio
async def test_mock_provider_success():
    """Verify MockAIProvider handles generate, stream, and embed cleanly."""
    mock_p = MockAIProvider(default_reply="Considered trip to Nongriat root bridges.")

    res = await mock_p.generate(messages=[{"role": "user", "content": "Hello"}])
    assert res.content == "Considered trip to Nongriat root bridges."
    assert mock_p.call_count == 1

    streamed = []
    async for token in mock_p.stream(messages=[{"role": "user", "content": "Hello"}]):
        streamed.append(token)
    assert "Nongriat" in "".join(streamed)

    embeddings = await mock_p.embed(["Test document line"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 256


@pytest.mark.asyncio
async def test_mock_provider_timeout_error():
    """Verify AIProviderTimeoutError is raised and returns status 504."""
    timeout_p = MockAIProvider(should_timeout=True)
    with pytest.raises(AIProviderTimeoutError) as exc_info:
        await timeout_p.generate(messages=[{"role": "user", "content": "Test timeout"}])
    assert exc_info.value.status_code == 504
    assert "timeout" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_mock_provider_auth_error():
    """Verify AIProviderAuthError is raised and returns status 502."""
    auth_p = MockAIProvider(should_fail_auth=True)
    with pytest.raises(AIProviderAuthError) as exc_info:
        await auth_p.generate(messages=[{"role": "user", "content": "Test auth"}])
    assert exc_info.value.status_code == 502


@pytest.mark.asyncio
async def test_mock_provider_rate_limit_error():
    """Verify AIProviderRateLimitError is raised and returns status 503."""
    rl_p = MockAIProvider(should_fail_rate_limit=True)
    with pytest.raises(AIProviderRateLimitError) as exc_info:
        await rl_p.generate(messages=[{"role": "user", "content": "Test rate limit"}])
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_mock_provider_retry_handling():
    """Verify provider retries on transient errors and succeeds once limit passed."""
    # Fails first 2 attempts, succeeds on 3rd
    retry_p = MockAIProvider(default_reply="Succeeded on retry.", fail_attempts=2)

    with pytest.raises(AIProviderError):
        await retry_p.generate(messages=[{"role": "user", "content": "Call 1"}])

    with pytest.raises(AIProviderError):
        await retry_p.generate(messages=[{"role": "user", "content": "Call 2"}])

    res = await retry_p.generate(messages=[{"role": "user", "content": "Call 3"}])
    assert res.content == "Succeeded on retry."


@pytest.mark.asyncio
async def test_credential_sanitization():
    """Verify API keys and Bearer tokens are stripped from error messages."""
    dirty_gemini = "Error: https://generativelanguage.googleapis.com?key=AIzaSyD_SECRET_KEY_123 failed"
    clean_gemini = sanitize_gemini(dirty_gemini)
    assert "AIzaSyD_SECRET_KEY_123" not in clean_gemini
    assert "key=[REDACTED]" in clean_gemini

    dirty_openai = "HTTP 401: Unauthorized request with header Authorization: Bearer sk-proj-SUPER_SECRET_123"
    clean_openai = sanitize_openai(dirty_openai)
    assert "sk-proj-SUPER_SECRET_123" not in clean_openai
    assert "Bearer [REDACTED]" in clean_openai


@pytest.mark.asyncio
async def test_provider_factory_resolution():
    """Verify get_ai_provider correctly instantiates each provider."""
    p_local = get_ai_provider("local")
    assert isinstance(p_local, LocalProvider)

    p_mock = get_ai_provider("mock")
    assert isinstance(p_mock, MockAIProvider)

    p_gemini = get_ai_provider("gemini")
    assert isinstance(p_gemini, GeminiProvider)

    p_openai = get_ai_provider("openai")
    assert isinstance(p_openai, OpenAIProvider)

    # Fallback to local for unknown
    p_unknown = get_ai_provider("non_existent_provider")
    assert isinstance(p_unknown, LocalProvider)


@pytest.mark.asyncio
async def test_unconfigured_cloud_providers_fail_safely():
    """Calling cloud providers without API key raises AIProviderAuthError without unhandled exceptions."""
    gemini_empty = GeminiProvider(api_key="")
    with pytest.raises(AIProviderAuthError):
        await gemini_empty.generate(messages=[{"role": "user", "content": "Hi"}])

    openai_empty = OpenAIProvider(api_key="")
    with pytest.raises(AIProviderAuthError):
        await openai_empty.generate(messages=[{"role": "user", "content": "Hi"}])
