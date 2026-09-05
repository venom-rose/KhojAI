import logging
from typing import Any, Dict, List, Optional
from backend.app.ai.prompts.system_prompts import (
    CONTEXT_SYNTHESIS_TEMPLATE,
    KHOJAI_AGENT_SYSTEM_PROMPT,
)
from backend.app.ai.tools.base import DataProvenance, ToolResult

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Assembles prompt messages and grounded tool results for the LLM."""

    def build_prompt_messages(
        self,
        user_message: str,
        tool_results: List[ToolResult],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Construct the sequence of messages sent to the AI provider."""
        messages: List[Dict[str, str]] = []

        # 1. System prompt & grounded tool context
        effective_system = system_prompt or KHOJAI_AGENT_SYSTEM_PROMPT

        if tool_results:
            results_str = "\n\n".join(res.format_for_llm() for res in tool_results)
            has_unverified = any(
                not res.is_live_data and res.provenance in (
                    DataProvenance.ESTIMATE_RECOMMENDATION,
                    DataProvenance.LOCAL_DATABASE,
                )
                for res in tool_results
            )
            disclaimer = ""
            if has_unverified:
                disclaimer = (
                    "\n> [CRITICAL GUARD]: Some or all tool data originated from local directory cache "
                    "or historical regional benchmarks. You MUST state clearly that pricing and availability are "
                    "indicative estimates or seasonal reference values, NOT live verified supplier confirmations."
                )

            effective_system += f"\n\n## Available Grounded Travel Tool Data:\n{results_str}{disclaimer}"

        messages.append({"role": "system", "content": effective_system})

        # 2. Previous conversation turns (if any)
        if conversation_history:
            for msg in conversation_history[-8:]:  # keep last 8 turns for tight context
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

        # 3. User message
        messages.append({"role": "user", "content": user_message})

        return messages
