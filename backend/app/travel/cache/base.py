"""Base abstract class for travel API response caching."""

from abc import ABC, abstractmethod
import hashlib
import json
from typing import Any, Optional


class BaseTravelCache(ABC):
    """Abstract caching interface for travel queries."""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl

    def make_key(self, prefix: str, **kwargs) -> str:
        """Generate a deterministic cache key from parameters."""
        sorted_items = sorted((k, str(v)) for k, v in kwargs.items() if v is not None)
        raw_repr = json.dumps(sorted_items, separators=(",", ":"), ensure_ascii=True)
        param_hash = hashlib.md5(raw_repr.encode("utf-8")).hexdigest()[:12]
        return f"travel:{prefix}:{param_hash}"

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached entry."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store an entry with a TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove a cached entry."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all entries."""
        pass
