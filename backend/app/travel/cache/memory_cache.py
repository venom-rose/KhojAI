"""Thread-safe, TTL-aware in-memory cache with LRU eviction."""

import logging
import time
from typing import Any, Dict, Optional, Tuple

from backend.app.travel.cache.base import BaseTravelCache

logger = logging.getLogger("khojai.travel.cache.memory")


class MemoryTravelCache(BaseTravelCache):
    """In-memory cache implementation with TTL expiration and max-size pruning."""

    def __init__(self, default_ttl: int = 3600, max_size: int = 2000):
        super().__init__(default_ttl=default_ttl)
        self.max_size = max_size
        self._store: Dict[str, Tuple[Any, float]] = {}
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        now = time.time()
        if key in self._store:
            value, expires_at = self._store[key]
            if expires_at > now:
                self._hits += 1
                logger.debug(f"Cache HIT [memory]: {key}")
                return value
            else:
                del self._store[key]
                logger.debug(f"Cache EXPIRED [memory]: {key}")

        self._misses += 1
        return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        # Evict oldest 10% if exceeding max_size
        if len(self._store) >= self.max_size:
            self._prune()

        ttl = ttl_seconds or self.default_ttl
        expires_at = time.time() + ttl
        self._store[key] = (value, expires_at)
        logger.debug(f"Cache SET [memory]: {key} (ttl={ttl}s)")

    async def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    async def clear(self) -> None:
        self._store.clear()
        logger.info("Memory travel cache cleared.")

    def _prune(self) -> None:
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._store.items() if exp <= now]
        for k in expired_keys:
            del self._store[k]
        # If still too large, drop oldest entries
        if len(self._store) >= self.max_size:
            drop_count = max(1, len(self._store) // 10)
            for k in list(self._store.keys())[:drop_count]:
                del self._store[k]

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._store),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_ratio": round(self._hits / max(1, self._hits + self._misses), 3),
        }
