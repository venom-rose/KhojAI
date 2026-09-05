import asyncio
import re
from typing import AsyncIterator, Dict, List, Optional
from backend.app.ai.base import AIResponse, BaseAIProvider


DEFAULT_KHOJAI_SYSTEM = (
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
    """Deterministic local AI provider for offline development, integration tests, and air-gapped environments."""

    def __init__(self, default_model: str = "khojai-local-v1"):
        self.default_model = default_model

    def _match_knowledge(self, query: str) -> tuple[str, list[str]]:
        lowered = query.lower()
        for item in OFFBEAT_KNOWLEDGE_BASE:
            if any(k in lowered for k in item["keywords"]):
                return item["reply"], item["citations"]

        # Default thoughtful reply
        return (
            "Thank you for sharing your travel curiosity. KHOJAI approaches Indian travel as a living field guide: "
            "prioritizing seasonal weather clarity, uncrowded trails, respectful community immersion, and unhurried itineraries. "
            "Could you tell me more about your preferred pace, duration, or whether you are leaning towards mountain stillness, "
            "coastal calm, or heritage craft corridors?",
            ["KhojAI Curated Intelligence", "Living Field Guide Network"]
        )

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AIResponse:
        """Synthesize response from conversation context."""
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "Hello"
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

    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens word by word with minimal async sleep."""
        last_user_msg = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "Hello"
        )
        reply_text, _ = self._match_knowledge(last_user_msg)

        # Split into small chunks (words and punctuation)
        chunks = re.findall(r"\S+|\s+", reply_text)
        for chunk in chunks:
            yield chunk
            await asyncio.sleep(0.005)  # simulate natural generation pace
