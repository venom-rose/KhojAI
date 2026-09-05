from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional


@dataclass
class AIResponse:
    """Standardized response container returned by all AI providers."""
    content: str
    model_name: str
    token_count: Optional[int] = None
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAIProvider(ABC):
    """Abstract base class defining the contract for all LLM providers in KHOJAI."""

    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AIResponse:
        """Generate a complete, non-streaming AI response.
        
        Args:
            messages: List of dicts with 'role' ('user'|'assistant'|'system') and 'content'.
            system_prompt: Optional system-level prompt guiding tone and persona.
            model: Optional model override.
            temperature: Sampling temperature between 0.0 and 1.0.
            
        Returns:
            AIResponse object containing text, model info, and metadata.
        """
        pass

    @abstractmethod
    async def stream_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens asynchronously as they are generated.
        
        Args:
            messages: List of dicts with 'role' and 'content'.
            system_prompt: Optional system-level prompt.
            model: Optional model override.
            temperature: Sampling temperature.
            
        Yields:
            Incremental string tokens/chunks.
        """
        pass
