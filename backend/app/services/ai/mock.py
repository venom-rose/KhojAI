from typing import Any, AsyncIterator, Dict, List, Optional, Union

from backend.app.services.ai.base import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIResponse,
    BaseAIProvider,
)


class MockAIProvider(BaseAIProvider):
    """Configurable mock AI provider for testing timeouts, retries, rate limits, and failure handling."""

    def __init__(
        self,
        default_reply: str = "Mocked AI travel response for testing.",
        default_model: str = "mock-model-v1",
        should_timeout: bool = False,
        should_fail_auth: bool = False,
        should_fail_rate_limit: bool = False,
        should_fail_server_error: bool = False,
        fail_attempts: int = 0,
    ):
        self.default_reply = default_reply
        self.default_model = default_model
        self.should_timeout = should_timeout
        self.should_fail_auth = should_fail_auth
        self.should_fail_rate_limit = should_fail_rate_limit
        self.should_fail_server_error = should_fail_server_error
        self.fail_attempts = fail_attempts

        self.call_count = 0
        self.last_messages: List[Dict[str, str]] = []
        self.last_system_prompt: Optional[str] = None

    def _check_injected_fault(self):
        self.call_count += 1

        # Transient failures testing retries
        if self.fail_attempts > 0 and self.call_count <= self.fail_attempts:
            raise AIProviderError(f"Simulated transient error attempt #{self.call_count}", provider="mock")

        if self.should_timeout:
            raise AIProviderTimeoutError("Mock provider simulated timeout.", provider="mock")
        if self.should_fail_auth:
            raise AIProviderAuthError("Mock provider simulated authentication error.", provider="mock")
        if self.should_fail_rate_limit:
            raise AIProviderRateLimitError("Mock provider simulated rate limit reached.", provider="mock")
        if self.should_fail_server_error:
            raise AIProviderError("Mock provider simulated server 500 error.", provider="mock")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AIResponse:
        self.last_messages = messages
        self.last_system_prompt = system_prompt
        self._check_injected_fault()

        return AIResponse(
            content=self.default_reply,
            model_name=model or self.default_model,
            token_count=len(self.default_reply.split()),
            finish_reason="stop",
            metadata={"mock": True, "call_count": self.call_count},
        )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        self.last_messages = messages
        self.last_system_prompt = system_prompt
        self._check_injected_fault()

        for word in self.default_reply.split():
            yield word + " "

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        self._check_injected_fault()
        if isinstance(texts, str):
            texts = [texts]
        # Return deterministic 256-dim mock vector
        return [[0.1] * 256 for _ in texts]
