import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter for API endpoints."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def _get_client_identifier(self, request: Request) -> str:
        # Prefer user token or forwarded IP, fallback to client host
        auth_header = request.headers.get("authorization", "")
        if auth_header:
            return auth_header
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check_rate_limit(self, request: Request) -> None:
        """Enforce rate limit. Raise 429 if limit is exceeded."""
        client_id = self._get_client_identifier(request)
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests outside window
        valid_timestamps = [t for t in self._requests[client_id] if t > window_start]
        self._requests[client_id] = valid_timestamps

        if len(valid_timestamps) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - valid_timestamps[0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.max_requests} requests per {self.window_seconds}s.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._requests[client_id].append(now)


# Default search rate limiter: 60 requests per minute
search_rate_limiter = SlidingWindowRateLimiter(max_requests=60, window_seconds=60)


def rate_limit_search(request: Request) -> None:
    """FastAPI dependency to rate limit search requests."""
    search_rate_limiter.check_rate_limit(request)
