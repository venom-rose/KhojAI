import asyncio
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from backend.app.ai.base import AIResponse, BaseAIProvider
from backend.app.ai.factory import get_ai_provider
from backend.app.ai.orchestration.context_builder import ContextBuilder
from backend.app.ai.orchestration.intent_detector import IntentDetector, UserIntent
from backend.app.ai.orchestration.tool_selector import ToolSelector
from backend.app.ai.tools.base import ToolResult
from backend.app.ai.tools.registry import ToolRegistry, default_tool_registry

logger = logging.getLogger(__name__)


class OrchestrationResult:
    """Detailed container for end-to-end orchestration output."""

    def __init__(
        self,
        final_content: str,
        intent: UserIntent,
        tools_called: List[str],
        tool_results: List[ToolResult],
        model_name: str,
        duration_ms: float,
        is_fully_live: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.final_content = final_content
        self.intent = intent
        self.tools_called = tools_called
        self.tool_results = tool_results
        self.model_name = model_name
        self.duration_ms = duration_ms
        self.is_fully_live = is_fully_live
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.final_content,
            "intent": self.intent.value,
            "tools_called": self.tools_called,
            "tool_results": [r.to_dict() for r in self.tool_results],
            "model_name": self.model_name,
            "duration_ms": self.duration_ms,
            "is_fully_live": self.is_fully_live,
            "metadata": self.metadata,
        }


class TravelOrchestrator:
    """Orchestrates the entire tool-using travel agent pipeline:
    
    User
    ↓
    AI Agent
    ↓
    Intent Detection
    ↓
    Tool Selection
    ↓
    Travel Tools
    ↓
    Results
    ↓
    Context Builder
    ↓
    LLM
    ↓
    Final Response
    """

    def __init__(
        self,
        ai_provider: Optional[BaseAIProvider] = None,
        tool_registry: Optional[ToolRegistry] = None,
        intent_detector: Optional[IntentDetector] = None,
        tool_selector: Optional[ToolSelector] = None,
        context_builder: Optional[ContextBuilder] = None,
    ):
        self.provider = ai_provider or get_ai_provider()
        self.registry = tool_registry or default_tool_registry
        self.intent_detector = intent_detector or IntentDetector()
        self.tool_selector = tool_selector or ToolSelector(registry=self.registry)
        self.context_builder = context_builder or ContextBuilder()

    async def execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """Execute resolved tools concurrently."""
        tasks = []
        for tc in tool_calls:
            tool_name = tc["tool_name"]
            kwargs = tc["kwargs"]
            tasks.append(self.registry.execute(tool_name, **kwargs))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results: List[ToolResult] = []
        for r in results:
            if isinstance(r, ToolResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                logger.error(f"Tool execution exception: {r}")
        return valid_results

    async def run(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> OrchestrationResult:
        """Execute the complete sync orchestration pipeline."""
        start_time = time.perf_counter()

        # 1. Intent Detection
        analysis = self.intent_detector.detect(user_message)
        logger.info(f"Intent detected: {analysis.intent.value} with tools: {analysis.required_tools}")

        # 2. Tool Selection
        tool_calls = self.tool_selector.resolve_tool_calls(
            analysis=analysis,
            user_query=user_message,
            user_id=user_id,
        )

        # 3. Travel Tools Execution
        tool_results = await self.execute_tools(tool_calls)
        tools_called = [tc["tool_name"] for tc in tool_calls]

        # 4. Context Builder
        prompt_messages = self.context_builder.build_prompt_messages(
            user_message=user_message,
            tool_results=tool_results,
            conversation_history=conversation_history,
        )

        # 5. LLM Synthesis
        ai_res: AIResponse = await self.provider.generate_response(
            messages=prompt_messages,
            model=model,
        )

        total_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_fully_live = bool(tool_results) and all(r.is_live_data for r in tool_results)

        return OrchestrationResult(
            final_content=ai_res.content,
            intent=analysis.intent,
            tools_called=tools_called,
            tool_results=tool_results,
            model_name=ai_res.model_name,
            duration_ms=total_ms,
            is_fully_live=is_fully_live,
            metadata={
                **ai_res.metadata,
                "entities": analysis.entities,
                "token_count": ai_res.token_count,
            },
        )

    async def stream_run(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[tuple[str, Optional[Dict[str, Any]]]]:
        """Stream response tokens while yielding tool lifecycle status events."""
        # 1. Intent Detection
        analysis = self.intent_detector.detect(user_message)

        # 2. Tool Selection
        tool_calls = self.tool_selector.resolve_tool_calls(
            analysis=analysis,
            user_query=user_message,
            user_id=user_id,
        )
        tools_called = [tc["tool_name"] for tc in tool_calls]

        # 3. Travel Tools Execution
        tool_results = await self.execute_tools(tool_calls)

        # 4. Context Builder
        prompt_messages = self.context_builder.build_prompt_messages(
            user_message=user_message,
            tool_results=tool_results,
            conversation_history=conversation_history,
        )

        # 5. Stream LLM tokens
        meta_event = {
            "intent": analysis.intent.value,
            "tools_called": tools_called,
            "tools_count": len(tools_called),
        }
        first = True

        async for chunk in self.provider.stream_response(
            messages=prompt_messages,
            model=model,
        ):
            if first:
                yield chunk, meta_event
                first = False
            else:
                yield chunk, None
