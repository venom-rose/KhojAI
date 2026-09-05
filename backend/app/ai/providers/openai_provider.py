import json
from typing import AsyncIterator, Dict, List, Optional
import httpx
from backend.app.ai.base import AIResponse, BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    """OpenAI AI Provider communicating via OpenAI Chat Completions API using httpx."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: str,
        default_model: str = "gpt-4o-mini",
        default_temperature: float = 0.7,
    ):
        self.api_key = api_key
        self.default_model = default_model
        self.default_temperature = default_temperature

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

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AIResponse:
        """Call OpenAI chat completions endpoint."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured on the server.")

        selected_model = model or self.default_model
        formatted_messages = self._prepare_messages(messages, system_prompt)

        payload = {
            "model": selected_model,
            "messages": formatted_messages,
            "temperature": temperature if temperature is not None else self.default_temperature,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        url = f"{self.BASE_URL}/chat/completions"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenAI API returned status {response.status_code}: {response.text}"
                )

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
                raise RuntimeError(f"Unexpected response structure from OpenAI API: {data}") from exc

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens from OpenAI chat completions endpoint."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured on the server.")

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

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"OpenAI streaming returned {response.status_code}: {error_text.decode('utf-8', errors='ignore')}")

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
