"""API key authentication for external agent access over Tailscale."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from sentinel.config import settings

_OPEN_PATHS = {"/api/health", "/api/ready"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Enforce X-API-Key on all /api/* routes when TAILSCALE_ENABLED=true.

    Skipped entirely when tailscale_enabled is false so local dev is unchanged.
    Health/ready endpoints are always open for monitoring.
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.tailscale_enabled:
            return await call_next(request)

        if request.url.path in _OPEN_PATHS:
            return await call_next(request)

        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if not provided or provided != settings.sentinel_api_key:
            return JSONResponse({"detail": "Invalid or missing API key"}, status_code=401)

        return await call_next(request)
