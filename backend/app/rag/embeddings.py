import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import List, Optional
import httpx

from backend.app.config.settings import settings


def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0

    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


class BaseEmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single string into a float vector."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a collection of text strings into float vectors."""
        pass


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, zero-dependency offline embedding provider based on hashed n-grams and L2 normalization."""

    DIMENSION = 256

    def _hash_token(self, token: str, dim: int) -> int:
        md5_int = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        return md5_int % dim

    def _generate_vector(self, text: str) -> List[float]:
        vector = [0.0] * self.DIMENSION
        clean_text = text.lower()
        tokens = re.findall(r"\b\w{2,}\b", clean_text)
        
        if not tokens:
            return vector

        # 1. Unigram frequency
        for token in tokens:
            idx = self._hash_token(token, self.DIMENSION)
            vector[idx] += 1.0

        # 2. Bigrams for phrases and context
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i+1]}"
            idx = self._hash_token(bigram, self.DIMENSION)
            vector[idx] += 1.5

        # 3. Substring tri-grams for spelling/morphology
        for token in tokens:
            if len(token) >= 3:
                for j in range(len(token) - 2):
                    trigram = token[j : j + 3]
                    idx = self._hash_token(f"char:{trigram}", self.DIMENSION)
                    vector[idx] += 0.3

        # 4. L2 Normalization
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0.0:
            vector = [v / norm for v in vector]

        return vector

    async def embed_text(self, text: str) -> List[float]:
        return self._generate_vector(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini text embedding API via HTTPX."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key: str, model: str = "text-embedding-004"):
        self.api_key = api_key
        self.model = model

    async def embed_text(self, text: str) -> List[float]:
        if not self.api_key:
            # Fallback to local if key is omitted
            return await LocalEmbeddingProvider().embed_text(text)

        url = f"{self.BASE_URL}/models/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text[:20000]}]},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                return data.get("embedding", {}).get("values", [])
            else:
                return await LocalEmbeddingProvider().embed_text(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        results = []
        for t in texts:
            results.append(await self.embed_text(t))
        return results


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI text embedding API via HTTPX."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model

    async def embed_text(self, text: str) -> List[float]:
        if not self.api_key:
            return await LocalEmbeddingProvider().embed_text(text)

        url = f"{self.BASE_URL}/embeddings"
        payload = {
            "model": self.model,
            "input": text[:8000],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                return data["data"][0]["embedding"]
            else:
                return await LocalEmbeddingProvider().embed_text(text)

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            return await LocalEmbeddingProvider().embed_batch(texts)

        url = f"{self.BASE_URL}/embeddings"
        payload = {
            "model": self.model,
            "input": [t[:8000] for t in texts],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                return [item["embedding"] for item in data.get("data", [])]
            else:
                return await LocalEmbeddingProvider().embed_batch(texts)


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Return the configured embedding provider."""
    provider = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider == "gemini" and (settings.GEMINI_API_KEY or settings.AI_API_KEY):
        return GeminiEmbeddingProvider(
            api_key=settings.GEMINI_API_KEY or settings.AI_API_KEY,
            model=settings.EMBEDDING_MODEL_NAME or "text-embedding-004",
        )
    elif provider == "openai" and (settings.OPENAI_API_KEY or settings.AI_API_KEY):
        return OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY or settings.AI_API_KEY,
            model="text-embedding-3-small",
        )
    else:
        return LocalEmbeddingProvider()
