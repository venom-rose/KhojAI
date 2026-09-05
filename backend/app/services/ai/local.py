import asyncio
import hashlib
import math
import re
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from backend.app.services.ai.base import AIResponse, BaseAIProvider

DEFAULT_SYSTEM = (
    "You are KHOJAI, an intelligent travel companion dedicated to uncovering offbeat, "
    "considered journeys across India. You favor quiet culture, unhurried pace, seasonal "
    "authenticity, and local nuance over commercial tourist traps."
)

OFFBEAT_KNOWLEDGE_BASE = [
    {
        "keywords": ["ziro", "arunachal", "apatani", "northeast"],
        "title": "Ziro Valley, Arunachal Pradesh",
        "reply": (
            "Ziro Valley offers an exceptional balance of agricultural wisdom and tranquil landscapes. "
            "Home to the Apatani tribe with their intricate sustainable paddy-cum-fish cultivation systems, "
            "it is best experienced between September and November when the pine-clad hills turn golden. "
            "Avoid rushing through; stay in a local homestay in Hong or Hari village to understand the living community heritage."
        ),
        "citations": ["Apatani Cultural Landscape", "Hong Village Community Stays"],
    },
    {
        "keywords": ["spiti", "himachal", "kaza", "tabo", "monastery", "high altitude"],
        "title": "Spiti Valley, Himachal Pradesh",
        "reply": (
            "Spiti rewards patience and deliberate pacing. Beyond the celebrated Key Gompa, take time for "
            "the 1,000-year-old mud murals of Tabo and the fossil villages of Langza and Hikkim. "
            "Plan at least 7 to 9 days to acclimatize properly via Shimla-Kinnaur rather than forcing a rapid ascent through Manali."
        ),
        "citations": ["Tabo Monastery Archaeological Reserve", "Langza Homestay Network"],
    },
    {
        "keywords": ["meghalaya", "cherrapunji", "sohra", "living root", "waterfall", "caves"],
        "title": "Meghalaya Highlands",
        "reply": (
            "Meghalaya reveals its finest character when you move past the crowded roadside viewpoints. "
            "In Nongriat and Tyrna, the living root bridges engineered by Khasi elders over centuries represent "
            "bio-architecture at its most profound. For a quieter base, consider Mawlyngbna or Shnongpdeng along the Umngot River."
        ),
        "citations": ["East Khasi Hills Bio-Architecture", "Mawlyngbna Community Conservation"],
    },
    {
        "keywords": ["kerala", "wayanad", "munnar", "backwaters", "alleppey", "south"],
        "title": "Quiet Corridors of Kerala",
        "reply": (
            "For a slower immersion in Kerala, step away from commercial houseboat hubs. Look toward the upper spice slopes of "
            "Wayanad's Tholpetty corridor or the heritage weavers of Chendamangalam. Early morning canoe journeys through narrow village "
            "canals in Kumarakom offer genuine stillness without the motorized diesel traffic."
        ),
        "citations": ["Chendamangalam Handloom Heritage", "Kuttanad Canal Stewardship"],
    },
    {
        "keywords": ["budget", "cost", "cheap", "price", "affordable"],
        "title": "Considered Budget Planning",
        "reply": (
            "Sustainable offbeat travel in India often costs significantly less than generic package tourism. "
            "By choosing verified village homestays (₹1,200–₹2,500/night including home-cooked meals) and local state transport, "
            "a 5-day journey can comfortably fit within ₹12,000 to ₹18,000 while ensuring your expenditure directly benefits local hosts."
        ),
        "citations": ["Community Homestay Tariffs", "Local Regional Transport Index"],
    },
]


class LocalProvider(BaseAIProvider):
    """Deterministic local AI provider executing text generation, streaming, and embeddings without network calls."""

    DIMENSION = 256

    def __init__(self, default_model: str = "khojai-local-v1"):
        self.default_model = default_model

    def _match_knowledge(self, query: str) -> tuple[str, list[str]]:
        lowered = query.lower()
        for item in OFFBEAT_KNOWLEDGE_BASE:
            if any(k in lowered for k in item["keywords"]):
                return item["reply"], item["citations"]

        return (
            "Thank you for sharing your travel curiosity. KHOJAI approaches Indian travel as a living field guide: "
            "prioritizing seasonal weather clarity, uncrowded trails, respectful community immersion, and unhurried itineraries. "
            "Could you tell me more about your preferred pace, duration, or whether you are leaning towards mountain stillness, "
            "coastal calm, or heritage craft corridors?",
            ["KhojAI Curated Intelligence", "Living Field Guide Network"],
        )

    async def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AIResponse:
        """Generate response deterministically from conversation messages."""
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "Hello",
        )
        reply_text, citations = self._match_knowledge(last_user_msg)
        used_model = model or self.default_model
        word_count = len(reply_text.split())

        return AIResponse(
            content=reply_text,
            model_name=used_model,
            token_count=int(word_count * 1.3),
            finish_reason="stop",
            metadata={
                "provider": "local",
                "citations": citations,
                "travel_tips": ["Carry local cash", "Respect quiet hours in heritage villages"],
            },
        )

    async def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream response tokens word by word with minimal async yield."""
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "Hello",
        )
        reply_text, _ = self._match_knowledge(last_user_msg)

        chunks = re.findall(r"\S+|\s+", reply_text)
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.002)

    def _hash_token(self, token: str, dim: int) -> int:
        return int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % dim

    def _generate_vector(self, text: str) -> List[float]:
        vector = [0.0] * self.DIMENSION
        clean_text = text.lower()
        tokens = re.findall(r"\b\w{2,}\b", clean_text)
        if not tokens:
            return vector

        for token in tokens:
            idx = self._hash_token(token, self.DIMENSION)
            vector[idx] += 1.0

        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i+1]}"
            idx = self._hash_token(bigram, self.DIMENSION)
            vector[idx] += 1.5

        for token in tokens:
            if len(token) >= 3:
                for j in range(len(token) - 2):
                    trigram = token[j : j + 3]
                    idx = self._hash_token(f"char:{trigram}", self.DIMENSION)
                    vector[idx] += 0.3

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0.0:
            vector = [v / norm for v in vector]
        return vector

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        **kwargs,
    ) -> List[List[float]]:
        """Generate normalized dense vectors for single or batch texts."""
        if isinstance(texts, str):
            texts = [texts]
        return [self._generate_vector(t) for t in texts]
