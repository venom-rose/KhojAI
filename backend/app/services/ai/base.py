from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Union


class AIProviderError(Exception):
    """Base exception for all AI provider errors. Never exposes raw credentials or stack traces."""
    def __init__(self, message: str, provider: str = "ai", status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code


class AIProviderTimeoutError(AIProviderError):
    """Raised when an AI provider request times out."""
    def __init__(self, message: str = "AI service request timed out.", provider: str = "ai"):
        super().__init__(message, provider=provider, status_code=504)


class AIProviderAuthError(AIProviderError):
    """Raised when provider credentials are invalid or unconfigured."""
    def __init__(self, message: str = "AI service authentication failure.", provider: str = "ai"):
        super().__init__(message, provider=provider, status_code=502)


class AIProviderRateLimitError(AIProviderError):
    """Raised when upstream AI provider rate limit is exceeded."""
    def __init__(self, message: str = "AI provider rate limit reached. Please try again shortly.", provider: str = "ai"):
        super().__init__(message, provider=provider, status_code=503)


@dataclass
class AIResponse:
    """Standardized response container returned by all AI providers."""
    content: str
    model_name: str
    token_count: Optional[int] = None
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAIProvider(ABC):
    """Provider-independent interface for generation, streaming, and embeddings.
    
    Subclasses must implement:
    - generate()
    - stream()
    - embed()
    """

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AIResponse:
        """Generate a complete AI response."""
        pass

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
        pass

    @abstractmethod
    async def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """Generate vector embeddings for input text(s). Returns list of float vectors."""
        pass

    # Aliases for backward compatibility with previous services
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AIResponse:
        return await self.generate(
            messages=messages,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            **kwargs,
        )

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        async for chunk in self.stream(
            messages=messages,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            **kwargs,
        ):
            yield chunk

    async def embed_text(self, text: str, model: Optional[str] = None) -> List[float]:
        res = await self.embed(texts=[text], model=model)
        return res[0] if res else []

    async def embed_batch(self, texts: List[str], model: Optional[str] = None) -> List[List[float]]:
        return await self.embed(texts=texts, model=model)
