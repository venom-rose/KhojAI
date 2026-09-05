import logging
import time
from typing import Any, Dict, List, Optional
from backend.app.ai.tools.base import BaseTool, DataProvenance, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry storing all travel tools for the AI Agent."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered AI tool: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        """Lookup tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """Return list of all registered tools."""
        return list(self._tools.values())

    def get_schemas(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Return function calling schemas for specified tools or all tools."""
        if tool_names:
            return [self._tools[name].get_schema() for name in tool_names if name in self._tools]
        return [tool.get_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool with error handling and timing."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                data=None,
                message=f"Tool '{tool_name}' is not registered.",
                provenance=DataProvenance.SYSTEM_STATE,
                is_live_data=False,
            )

        start = time.perf_counter()
        try:
            result = await tool.execute(**kwargs)
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            result.metadata["execution_time_ms"] = duration_ms
            return result
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(f"Error executing tool '{tool_name}': {exc}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                data=None,
                message=str(exc),
                provenance=DataProvenance.SYSTEM_STATE,
                is_live_data=False,
                metadata={"execution_time_ms": duration_ms, "error": str(exc)},
            )


# Default shared registry instance
default_tool_registry = ToolRegistry()
