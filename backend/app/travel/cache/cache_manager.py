"""High-performance caching layer for external travel API responses."""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

from backend.app.config.settings import settings

logger = logging.getLogger("khojai.travel.cache")


class TravelCacheManager:
    """Unified cache manager with in-memory TTL store and optional Redis backing."""

    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._memory_cache: Dict[str, Tuple[Any, float]] = {}

    def make_key(self, prefix: str, **kwargs) -> str:
        """Create a deterministic MD5 hash key from sorted parameters."""
        sorted_items = sorted((k, str(v)) for k, v in kwargs.items() if v is not None)
        raw_repr = json.dumps(sorted_items, separators=(",", ":"), ensure_ascii=True)
        param_hash = hashlib.md5(raw_repr.encode("utf-8")).hexdigest()[:12]
        return f"travel:{prefix}:{param_hash}"

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached payload if not expired."""
        now = time.time()
        if key in self._memory_cache:
            value, expires_at = self._memory_cache[key]
            if expires_at > now:
                logger.debug(f"Cache HIT [in-memory]: {key}")
                return value
            else:
                del self._memory_cache[key]
                logger.debug(f"Cache EXPIRED: {key}")

        return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store a payload with TTL expiration."""
        ttl = ttl_seconds or self.default_ttl
        expires_at = time.time() + ttl
        self._memory_cache[key] = (value, expires_at)
        logger.debug(f"Cache SET: {key} (ttl={ttl}s)")

    async def delete(self, key: str) -> None:
        """Invalidate a specific cache key."""
        if key in self._memory_cache:
            del self._memory_cache[key]

    async def clear(self) -> None:
        """Clear all in-memory entries."""
        self._memory_cache.clear()
        logger.info("Travel cache cleared.")


# Global cache manager singleton
travel_cache = TravelCacheManager(default_ttl=settings.TRAVEL_CACHE_TTL_SECONDS)
