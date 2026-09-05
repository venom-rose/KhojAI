import asyncio
import json
import logging
import re
from typing import Any, AsyncIterator, Dict, List, Optional, Union
import httpx

from backend.app.config.settings import settings
from backend.app.services.ai.base import (
    AIProviderAuthError,
    AIProviderError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    AIResponse,
    BaseAIProvider,
)

logger = logging.getLogger(__name__)


def _sanitize_error_text(text: str) -> str:
    """Mask any Bearer token or authorization string."""
    return re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", text)


class OpenAIProvider(BaseAIProvider):
    """OpenAI AI Provider with unified generate, stream, embed, timeout, and retry handling."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4o-mini",
        default_embedding_model: str = "text-embedding-3-small",
        default_temperature: float = 0.7,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = api_key
        self.default_model = default_model
        self.default_embedding_model = default_embedding_model
        self.default_temperature = default_temperature
        self.timeout_seconds = timeout_seconds or settings.AI_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.AI_MAX_RETRIES

    def _prepare_messages(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        formatted = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        for m in messages:
            formatted.append({
                "role": m.get("role", "user"),
                "content": m.get("content", ""),
            })
        return formatted

    async def _post_with_retry(self, url: str, json_data: dict) -> httpx.Response:
        """Execute POST request with timeout and exponential backoff retry."""
        if not self.api_key:
            raise AIProviderAuthError("OPENAI_API_KEY is not configured on the server.", provider="openai")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(url, json=json_data, headers=headers)

                if response.status_code == 200:
                    return response

                if response.status_code in (401, 403):
                    raise AIProviderAuthError("OpenAI authentication failed. Invalid API key.", provider="openai")

                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (2 ** attempt))
                        continue
                    raise AIProviderRateLimitError("OpenAI rate limit reached. Please try again shortly.", provider="openai")

                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (2 ** attempt))
                        continue
                    clean_msg = _sanitize_error_text(response.text)
                    raise AIProviderError(f"OpenAI server error ({response.status_code}): {clean_msg}", provider="openai")

                clean_msg = _sanitize_error_text(response.text)
                raise AIProviderError(f"OpenAI request failed ({response.status_code}): {clean_msg}", provider="openai")

            except httpx.TimeoutException as te:
                last_exc = te
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise AIProviderTimeoutError(f"OpenAI request timed out after {self.timeout_seconds}s.", provider="openai") from te
            except (AIProviderError, AIProviderAuthError, AIProviderRateLimitError, AIProviderTimeoutError):
                raise
            except Exception as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise AIProviderError(f"Unexpected communication error with OpenAI: {_sanitize_error_text(str(e))}", provider="openai") from e

        raise AIProviderError(f"OpenAI call failed after {self.max_retries} attempts: {_sanitize_error_text(str(last_exc))}", provider="openai")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AIResponse:
        """Call OpenAI chat completions endpoint with retry & timeout."""
        selected_model = model or self.default_model
        formatted_messages = self._prepare_messages(messages, system_prompt)

        payload = {
            "model": selected_model,
            "messages": formatted_messages,
            "temperature": temperature if temperature is not None else self.default_temperature,
        }

        url = f"{self.BASE_URL}/chat/completions"
        response = await self._post_with_retry(url, payload)

        data = response.json()
        try:
            choice = data["choices"][0]
            text = choice["message"]["content"]
            finish_reason = choice.get("finish_reason", "stop")
            usage = data.get("usage", {})
            token_count = usage.get("total_tokens", len(text.split()))

            return AIResponse(
                content=text,
                model_name=selected_model,
                token_count=token_count,
                finish_reason=finish_reason,
                metadata={"usage": usage, "provider": "openai"},
            )
        except (KeyError, IndexError) as exc:
            raise AIProviderError("Unexpected response format from OpenAI API.", provider="openai") from exc

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream chunks from OpenAI chat completions."""
        if not self.api_key:
            raise AIProviderAuthError("OPENAI_API_KEY is not configured.", provider="openai")

        selected_model = model or self.default_model
        formatted_messages = self._prepare_messages(messages, system_prompt)

        payload = {
            "model": selected_model,
            "messages": formatted_messages,
            "temperature": temperature if temperature is not None else self.default_temperature,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.BASE_URL}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    if response.status_code == 401 or response.status_code == 403:
                        raise AIProviderAuthError("OpenAI streaming authentication failed.", provider="openai")
                    if response.status_code == 429:
                        raise AIProviderRateLimitError("OpenAI streaming rate limit reached.", provider="openai")
                    if response.status_code != 200:
                        err_text = await response.aread()
                        raise AIProviderError(f"OpenAI streaming failed ({response.status_code}): {_sanitize_error_text(err_text.decode('utf-8', errors='ignore'))}", provider="openai")

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_data = json.loads(data_str)
                                choices = chunk_data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
        except httpx.TimeoutException as te:
            raise AIProviderTimeoutError("OpenAI streaming timed out.", provider="openai") from te
        except (AIProviderError, AIProviderAuthError, AIProviderRateLimitError, AIProviderTimeoutError):
            raise
        except Exception as e:
            raise AIProviderError(f"OpenAI streaming connection error: {_sanitize_error_text(str(e))}", provider="openai") from e

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """Call OpenAI embeddings endpoint."""
        if isinstance(texts, str):
            texts = [texts]

        selected_model = model or self.default_embedding_model
        payload = {
            "model": selected_model,
            "input": [t[:8000] for t in texts],
        }

        url = f"{self.BASE_URL}/embeddings"
        response = await self._post_with_retry(url, payload)
        data = response.json()
        return [item["embedding"] for item in data.get("data", [])]
