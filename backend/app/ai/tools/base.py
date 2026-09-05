from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DataProvenance(str, Enum):
    """Indicates where tool result data originated and its reliability level."""
    LIVE_API = "live_api"
    LOCAL_DATABASE = "local_database"
    ESTIMATE_RECOMMENDATION = "estimate_recommendation"
    CALCULATED = "calculated"
    SYSTEM_STATE = "system_state"


@dataclass
class ToolResult:
    """Standardized response from any travel tool execution."""
    tool_name: str
    success: bool
    data: Any
    message: Optional[str] = None
    provenance: DataProvenance = DataProvenance.ESTIMATE_RECOMMENDATION
    is_live_data: bool = False
    warning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "provenance": self.provenance.value,
            "is_live_data": self.is_live_data,
            "warning": self.warning,
            "metadata": self.metadata,
        }

    def format_for_llm(self) -> str:
        """Format the result as a grounded context snippet for the LLM."""
        header = f"### Tool Result: {self.tool_name} [{self.provenance.value.upper()}]"
        if not self.is_live_data and self.provenance in (
            DataProvenance.ESTIMATE_RECOMMENDATION,
            DataProvenance.LOCAL_DATABASE,
        ):
            note = (
                "\n*Notice: Real-time live booking/price confirmation is currently unavailable. "
                "The figures/details below are curated estimates or reference values, NOT guaranteed live quotes.*"
            )
        else:
            note = ""

        if not self.success:
            return f"{header}\nStatus: Failed\nError: {self.message}"

        import json
        try:
            formatted_data = json.dumps(self.data, indent=2, default=str)
        except Exception:
            formatted_data = str(self.data)

        return f"{header}{note}\n```json\n{formatted_data}\n```"


class BaseTool(ABC):
    """Abstract base class for all KHOJAI travel tools."""

    name: str
    description: str
    parameters: Dict[str, Any]

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with validated kwargs and return a ToolResult."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Return OpenAI/Gemini compatible JSON Schema definition for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
