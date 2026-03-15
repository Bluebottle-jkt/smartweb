"""
Simple in-memory sliding-window rate limiter middleware.

Does NOT require slowapi or Redis — suitable for intranet deployments.
Limits: 50 requests / user / minute  (configurable via environment).
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# ── Configuration ─────────────────────────────────────────────────────────────
_DEFAULT_LIMIT = 50          # requests per window
_WINDOW_SECONDS = 60         # sliding window length

# Stricter limits for expensive operations
_ENDPOINT_LIMITS: dict[str, int] = {
    "/network/search":        20,
    "/network/ai-discovery":  10,
    "/network/path":          15,
    "/network/sync":          5,
}


class _UserBucket:
    """Sliding window counter per (user, endpoint_prefix) pair."""

    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self._timestamps: Deque[float] = deque()

    def is_allowed(self) -> bool:
        now = time.monotonic()
        # Evict old entries
        cutoff = now - self.window
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()
        if len(self._timestamps) >= self.limit:
            return False
        self._timestamps.append(now)
        return True

    def remaining(self) -> int:
        now = time.monotonic()
        cutoff = now - self.window
        active = sum(1 for t in self._timestamps if t >= cutoff)
        return max(0, self.limit - active)

    def reset_at(self) -> int:
        if self._timestamps:
            return int(self._timestamps[0] + self.window)
        return int(time.monotonic() + self.window)


# ── In-memory store: keyed by (user_key, effective_limit) ────────────────────
_buckets: dict[tuple[str, int], _UserBucket] = defaultdict(
    lambda: _UserBucket(_DEFAULT_LIMIT, _WINDOW_SECONDS)
)


def _get_user_key(request: Request) -> str:
    """Derive a stable per-user key from session cookie or IP."""
    # Try to get username from request state (set by auth middleware)
    user = getattr(request.state, "current_user", None)
    if user and hasattr(user, "username"):
        return f"user:{user.username}"
    # Fall back to IP
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"ip:{ip}"


def _endpoint_limit(path: str) -> int:
    for prefix, limit in _ENDPOINT_LIMITS.items():
        if path.startswith(prefix):
            return limit
    return _DEFAULT_LIMIT


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Applies sliding-window rate limiting.
    Exempt paths: /health, /docs, /openapi.json, /auth/login.
    """

    EXEMPT = {"/health", "/", "/docs", "/openapi.json", "/redoc", "/auth/login", "/auth/logout"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip exempt endpoints and static assets
        if path in self.EXEMPT or path.startswith("/static"):
            return await call_next(request)

        user_key = _get_user_key(request)
        limit = _endpoint_limit(path)
        bucket_key = (user_key, limit)

        if bucket_key not in _buckets:
            _buckets[bucket_key] = _UserBucket(limit, _WINDOW_SECONDS)

        bucket = _buckets[bucket_key]

        if not bucket.is_allowed():
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Slow down and try again.",
                    "limit": limit,
                    "window_seconds": _WINDOW_SECONDS,
                },
                headers={
                    "Retry-After": str(_WINDOW_SECONDS),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(bucket.reset_at()),
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(bucket.remaining())
        response.headers["X-RateLimit-Reset"] = str(bucket.reset_at())
        return response
