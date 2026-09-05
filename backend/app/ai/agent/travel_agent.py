import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional
from backend.app.ai.base import BaseAIProvider
from backend.app.ai.factory import get_ai_provider
from backend.app.ai.orchestration.orchestrator import (
    OrchestrationResult,
    TravelOrchestrator,
)
from backend.app.ai.tools.registry import ToolRegistry, default_tool_registry

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """Standardized high-level agent response."""
    content: str
    intent: str
    tools_used: List[str]
    is_live: bool
    duration_ms: float
    model_name: str
    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "intent": self.intent,
            "tools_used": self.tools_used,
            "is_live": self.is_live,
            "duration_ms": self.duration_ms,
            "model_name": self.model_name,
            "tool_results": self.tool_results,
            "metadata": self.metadata,
        }


class TravelAgent:
    """High-level KHOJAI AI Travel Agent that dynamically uses specialized travel tools."""

    def __init__(
        self,
        ai_provider: Optional[BaseAIProvider] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.provider = ai_provider or get_ai_provider()
        self.registry = tool_registry or default_tool_registry
        self.orchestrator = TravelOrchestrator(
            ai_provider=self.provider,
            tool_registry=self.registry,
        )

    async def run(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentResponse:
        """Run the full agent orchestration pipeline synchronously."""
        result: OrchestrationResult = await self.orchestrator.run(
            user_message=user_message,
            conversation_history=conversation_history,
            user_id=user_id,
            model=model,
        )

        return AgentResponse(
            content=result.final_content,
            intent=result.intent.value,
            tools_used=result.tools_called,
            is_live=result.is_fully_live,
            duration_ms=result.duration_ms,
            model_name=result.model_name,
            tool_results=[r.to_dict() for r in result.tool_results],
            metadata=result.metadata,
        )

    async def stream_run(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[tuple[str, Optional[Dict[str, Any]]]]:
        """Stream response tokens while yielding tool activity metadata."""
        async for chunk, meta in self.orchestrator.stream_run(
            user_message=user_message,
            conversation_history=conversation_history,
            user_id=user_id,
            model=model,
        ):
            yield chunk, meta


# Global default agent instance
travel_agent = TravelAgent()
