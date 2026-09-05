import logging
from typing import Optional
from backend.app.ai.base import BaseAIProvider
from backend.app.ai.providers.gemini_provider import GeminiProvider
from backend.app.ai.providers.local_provider import LocalProvider
from backend.app.ai.providers.openai_provider import OpenAIProvider
from backend.app.config.settings import settings

logger = logging.getLogger(__name__)


def get_ai_provider(provider_name: Optional[str] = None) -> BaseAIProvider:
    """Factory function returning the active AIProvider instance.
    
    Dynamically resolved based on environment configuration or override.
    Supported: 'local' (default/offline), 'gemini', 'openai'.
    """
    provider = (provider_name or settings.AI_PROVIDER).lower().strip()

    if provider == "gemini":
        api_key = settings.GEMINI_API_KEY or settings.AI_API_KEY
        return GeminiProvider(
            api_key=api_key,
            default_model=settings.GEMINI_MODEL_NAME or settings.AI_MODEL_NAME,
            default_temperature=settings.AI_TEMPERATURE,
        )
    elif provider == "openai":
        api_key = settings.OPENAI_API_KEY or settings.AI_API_KEY
        return OpenAIProvider(
            api_key=api_key,
            default_model=settings.OPENAI_MODEL_NAME,
            default_temperature=settings.AI_TEMPERATURE,
        )
    elif provider in ("local", "mock", "offline"):
        return LocalProvider(default_model=settings.AI_MODEL_NAME or "khojai-local-v1")
    else:
        logger.warning("Unrecognized AI_PROVIDER '%s'. Falling back to LocalProvider.", provider)
        return LocalProvider(default_model=settings.AI_MODEL_NAME or "khojai-local-v1")
