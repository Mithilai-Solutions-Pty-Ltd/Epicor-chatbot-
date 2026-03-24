"""
============================================================
Rate Limiter Middleware
============================================================
Simple per-IP sliding-window rate limiter.
Default: 60 requests/minute.
Prevents abuse on the public Render endpoint.
============================================================
"""

import time
import logging
from collections import defaultdict, deque
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("botzi.rate_limiter")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.window = 60  # seconds
        # { ip: deque of timestamps }
        self._calls: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health / ping
        if request.url.path in ("/api/health", "/api/ping", "/"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        calls = self._calls[ip]

        # Remove calls outside the rolling window
        while calls and calls[0] < now - self.window:
            calls.popleft()

        if len(calls) >= self.rpm:
            logger.warning(f"Rate limit exceeded for IP {ip}")
            return Response(
                content='{"error":"Rate limit exceeded. Try again in a minute."}',
                status_code=429,
                media_type="application/json",
            )

        calls.append(now)
        return await call_next(request)
