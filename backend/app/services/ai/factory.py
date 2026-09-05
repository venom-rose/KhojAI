import logging
from typing import Optional
from backend.app.config.settings import settings
from backend.app.services.ai.base import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIResponse,
    BaseAIProvider,
)
from backend.app.services.ai.gemini import GeminiProvider
from backend.app.services.ai.local import LocalProvider
from backend.app.services.ai.mock import MockAIProvider
from backend.app.services.ai.openai import OpenAIProvider

logger = logging.getLogger(__name__)


def get_ai_provider(provider_name: Optional[str] = None) -> BaseAIProvider:
    """Factory function resolving the active AI provider based on environment configuration or override."""
    provider = (provider_name or settings.AI_PROVIDER).lower().strip()

    if provider == "gemini":
        api_key = settings.GEMINI_API_KEY or settings.AI_API_KEY
        return GeminiProvider(
            api_key=api_key,
            default_model=settings.GEMINI_MODEL_NAME or settings.AI_MODEL_NAME,
            default_embedding_model=settings.EMBEDDING_MODEL_NAME,
            default_temperature=settings.AI_TEMPERATURE,
            timeout_seconds=settings.AI_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )
    elif provider == "openai":
        api_key = settings.OPENAI_API_KEY or settings.AI_API_KEY
        return OpenAIProvider(
            api_key=api_key,
            default_model=settings.OPENAI_MODEL_NAME,
            default_embedding_model="text-embedding-3-small",
            default_temperature=settings.AI_TEMPERATURE,
            timeout_seconds=settings.AI_TIMEOUT_SECONDS,
            max_retries=settings.AI_MAX_RETRIES,
        )
    elif provider == "mock":
        return MockAIProvider()
    elif provider in ("local", "offline"):
        return LocalProvider(default_model=settings.AI_MODEL_NAME or "khojai-local-v1")
    else:
        logger.warning("Unrecognized AI_PROVIDER '%s'. Falling back to LocalProvider.", provider)
        return LocalProvider(default_model=settings.AI_MODEL_NAME or "khojai-local-v1")
