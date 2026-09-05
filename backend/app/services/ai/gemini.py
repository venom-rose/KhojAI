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
    """Strip any accidental API key or internal credentials from error messages."""
    return re.sub(r"key=[^&\s'\"]+", "key=[REDACTED]", text)


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider with unified generate, stream, embed, timeout, and retry handling."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        default_model: str = "gemini-1.5-flash",
        default_embedding_model: str = "text-embedding-004",
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

    def _convert_messages(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None):
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            gemini_role = "model" if role in ("assistant", "model") else "user"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": msg.get("content", "")}],
            })

        system_instruction = None
        if system_prompt:
            system_instruction = {"parts": [{"text": system_prompt}]}

        return contents, system_instruction

    async def _post_with_retry(self, url: str, json_data: dict) -> httpx.Response:
        """Execute POST request with timeout and exponential backoff retry."""
        if not self.api_key:
            raise AIProviderAuthError("GEMINI_API_KEY is not configured on the server.", provider="gemini")

        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(url, json=json_data)

                # Check HTTP status
                if response.status_code == 200:
                    return response

                if response.status_code in (401, 403):
                    raise AIProviderAuthError("Gemini authentication failed. Please verify API key.", provider="gemini")

                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1.0 * (2 ** attempt))
                        continue
                    raise AIProviderRateLimitError("Gemini rate limit exceeded. Please try again shortly.", provider="gemini")

                if response.status_code >= 500:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (2 ** attempt))
                        continue
                    clean_msg = _sanitize_error_text(response.text)
                    raise AIProviderError(f"Gemini server error ({response.status_code}): {clean_msg}", provider="gemini")

                clean_msg = _sanitize_error_text(response.text)
                raise AIProviderError(f"Gemini request failed ({response.status_code}): {clean_msg}", provider="gemini")

            except httpx.TimeoutException as te:
                last_exc = te
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise AIProviderTimeoutError(f"Gemini request timed out after {self.timeout_seconds}s.", provider="gemini") from te
            except (AIProviderError, AIProviderAuthError, AIProviderRateLimitError, AIProviderTimeoutError):
                raise
            except Exception as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                    continue
                raise AIProviderError(f"Unexpected communication error with Gemini: {_sanitize_error_text(str(e))}", provider="gemini") from e

        raise AIProviderError(f"Gemini call failed after {self.max_retries} attempts: {_sanitize_error_text(str(last_exc))}", provider="gemini")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AIResponse:
        """Call Gemini generateContent endpoint with retry & timeout."""
        selected_model = model or self.default_model
        contents, system_instruction = self._convert_messages(messages, system_prompt)

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature if temperature is not None else self.default_temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.BASE_URL}/models/{selected_model}:generateContent?key={self.api_key}"
        response = await self._post_with_retry(url, payload)

        data = response.json()
        try:
            candidate = data["candidates"][0]
            text = candidate["content"]["parts"][0]["text"]
            finish_reason = candidate.get("finishReason", "stop")
            usage = data.get("usageMetadata", {})
            token_count = usage.get("totalTokenCount", len(text.split()))

            return AIResponse(
                content=text,
                model_name=selected_model,
                token_count=token_count,
                finish_reason=finish_reason.lower(),
                metadata={"usage": usage, "provider": "gemini"},
            )
        except (KeyError, IndexError) as exc:
            raise AIProviderError("Unexpected response format from Gemini API.", provider="gemini") from exc

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream chunks from Gemini streamGenerateContent."""
        if not self.api_key:
            raise AIProviderAuthError("GEMINI_API_KEY is not configured.", provider="gemini")

        selected_model = model or self.default_model
        contents, system_instruction = self._convert_messages(messages, system_prompt)

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature if temperature is not None else self.default_temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.BASE_URL}/models/{selected_model}:streamGenerateContent?alt=sse&key={self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code == 401 or response.status_code == 403:
                        raise AIProviderAuthError("Gemini streaming authentication failed.", provider="gemini")
                    if response.status_code == 429:
                        raise AIProviderRateLimitError("Gemini streaming rate limit reached.", provider="gemini")
                    if response.status_code != 200:
                        err_text = await response.aread()
                        raise AIProviderError(f"Gemini streaming failed ({response.status_code}): {_sanitize_error_text(err_text.decode('utf-8', errors='ignore'))}", provider="gemini")

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if not data_str:
                                continue
                            try:
                                chunk_data = json.loads(data_str)
                                candidates = chunk_data.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for p in parts:
                                        if "text" in p:
                                            yield p["text"]
                            except json.JSONDecodeError:
                                continue
        except httpx.TimeoutException as te:
            raise AIProviderTimeoutError("Gemini streaming timed out.", provider="gemini") from te
        except (AIProviderError, AIProviderAuthError, AIProviderRateLimitError, AIProviderTimeoutError):
            raise
        except Exception as e:
            raise AIProviderError(f"Gemini streaming connection error: {_sanitize_error_text(str(e))}", provider="gemini") from e

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """Call Gemini embedContent for text embeddings."""
        if isinstance(texts, str):
            texts = [texts]

        selected_model = model or self.default_embedding_model
        results = []

        for text in texts:
            url = f"{self.BASE_URL}/models/{selected_model}:embedContent?key={self.api_key}"
            payload = {
                "model": f"models/{selected_model}",
                "content": {"parts": [{"text": text[:20000]}]},
            }
            res = await self._post_with_retry(url, payload)
            data = res.json()
            values = data.get("embedding", {}).get("values", [])
            results.append(values)

        return results
