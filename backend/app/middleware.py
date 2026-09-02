"""HTTP middleware: per-request correlation ids + a dependency-free rate limiter.

Both are plain ASGI/Starlette ``BaseHTTPMiddleware`` classes wired up in
app/main.py. Neither needs Redis or any extra package — the trade-off is
that the rate-limit counters live in this process's memory, so on a
multi-instance deployment each replica enforces the limit independently.
For that case, put a real gateway / shared store in front instead (and set
``RATE_LIMIT_ENABLED=false`` here so you're not limiting twice).
"""

import hashlib
import logging
import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings
from app.logging_config import request_id_ctx

logger = logging.getLogger("app.request")

# Endpoints that are cheap to call but expensive or sensitive to serve get
# the tighter bucket: auth (password brute-force), the LLM-backed routes,
# and batch upload (PDF rasterization + OCR).
_HEAVY_PREFIXES = ("/api/auth/login", "/api/auth/register", "/api/predict", "/api/assist")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns each request an id, echoes it back as ``X-Request-ID``, and
    logs a one-line access record with wall-clock duration."""

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "").strip()
        request_id = incoming[:64] or uuid.uuid4().hex[:12]
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "%s %s -> unhandled exception after %.0fms",
                request.method,
                request.url.path,
                elapsed_ms,
            )
            raise
        finally:
            request_id_ctx.reset(token)

        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-cost sliding-window limiter keyed by bearer token (falls back
    to client IP for unauthenticated calls). Only mutating requests count;
    GETs — dashboards, history polling — are never limited."""

    def __init__(self, app):
        super().__init__(app)
        # key -> deque[timestamps]; trimmed lazily on each hit.
        self._hits: dict[str, deque] = defaultdict(deque)
        self._window = max(1, settings.RATE_LIMIT_WINDOW_SECONDS)
        self._default_limit = max(1, settings.RATE_LIMIT_REQUESTS)
        self._heavy_limit = max(1, settings.RATE_LIMIT_HEAVY_REQUESTS)

    def _client_key(self, request: Request) -> str:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            # Hash so raw tokens never land in memory dumps / logs.
            return "t:" + hashlib.sha256(auth[7:].encode()).hexdigest()[:16]
        client = request.client.host if request.client else "unknown"
        return "ip:" + client

    def _limit_for(self, path: str) -> int:
        if any(path.startswith(p) for p in _HEAVY_PREFIXES):
            return self._heavy_limit
        return self._default_limit

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED or request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        limit = self._limit_for(request.url.path)
        key = self._client_key(request) + "|" + ("heavy" if limit == self._heavy_limit else "std")
        now = time.monotonic()
        bucket = self._hits[key]

        cutoff = now - self._window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = max(1, int(self._window - (now - bucket[0])))
            logger.warning("rate limit hit: %s %s (key=%s)", request.method, request.url.path, key)
            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        f"Rate limit exceeded ({limit} requests per "
                        f"{self._window}s). Try again in {retry_after}s."
                    )
                },
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)

        # Opportunistic housekeeping so idle keys don't leak memory forever.
        if len(self._hits) > 4096:
            self._evict_stale(cutoff)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(bucket)))
        return response

    def _evict_stale(self, cutoff: float) -> None:
        for k in [k for k, v in self._hits.items() if not v or v[-1] < cutoff]:
            self._hits.pop(k, None)
