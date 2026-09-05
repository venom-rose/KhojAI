import json
from typing import AsyncIterator, Dict, List, Optional
import httpx
from backend.app.ai.base import AIResponse, BaseAIProvider


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider communicating via Gemini REST API using httpx."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        default_model: str = "gemini-1.5-flash",
        default_temperature: float = 0.7,
    ):
        self.api_key = api_key
        self.default_model = default_model
        self.default_temperature = default_temperature

    def _convert_messages(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None):
        """Convert standard role/content messages to Gemini contents structure."""
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            # Map role to gemini roles: 'user' or 'model'
            gemini_role = "model" if role in ("assistant", "model") else "user"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": msg.get("content", "")}],
            })

        system_instruction = None
        if system_prompt:
            system_instruction = {
                "parts": [{"text": system_prompt}]
            }

        return contents, system_instruction

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AIResponse:
        """Call Gemini generateContent endpoint."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured on the server.")

        selected_model = model or self.default_model
        contents, system_instruction = self._convert_messages(messages, system_prompt)

        payload: Dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature if temperature is not None else self.default_temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.BASE_URL}/models/{selected_model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Gemini API returned status {response.status_code}: {response.text}"
                )

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
                raise RuntimeError(f"Unexpected response structure from Gemini API: {data}") from exc

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """Stream response chunks from Gemini streamGenerateContent endpoint."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured on the server.")

        selected_model = model or self.default_model
        contents, system_instruction = self._convert_messages(messages, system_prompt)

        payload: Dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature if temperature is not None else self.default_temperature,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.BASE_URL}/models/{selected_model}:streamGenerateContent?alt=sse"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise RuntimeError(f"Gemini streaming returned {response.status_code}: {error_text.decode('utf-8', errors='ignore')}")

                buffer = ""
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
