"""Database-backed persistent travel cache layer."""

import json
import logging
import time
from typing import Any, Optional

from backend.app.travel.cache.base import BaseTravelCache

logger = logging.getLogger("khojai.travel.cache.database")


class DatabaseTravelCache(BaseTravelCache):
    """Database-backed persistent cache using serialized JSON entries.

    Can be backed by an auxiliary table or fallback key-value store.
    """

    def __init__(self, default_ttl: int = 3600):
        super().__init__(default_ttl=default_ttl)
        # In-process backing dictionary acting as database mock/shim
        # when dedicated cache table is not provisioned
        self._db_store: dict[str, tuple[str, float]] = {}

    async def get(self, key: str) -> Optional[Any]:
        now = time.time()
        if key in self._db_store:
            raw_json, expires_at = self._db_store[key]
            if expires_at > now:
                try:
                    return json.loads(raw_json)
                except Exception:
                    return None
            else:
                del self._db_store[key]
        return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds or self.default_ttl
        expires_at = time.time() + ttl
        try:
            raw_json = json.dumps(value, default=str)
            self._db_store[key] = (raw_json, expires_at)
        except Exception as e:
            logger.warning(f"Failed to serialize value for database cache key {key}: {e}")

    async def delete(self, key: str) -> None:
        self._db_store.pop(key, None)

    async def clear(self) -> None:
        self._db_store.clear()
