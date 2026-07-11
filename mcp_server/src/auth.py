from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import get_config


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Health probes bypass auth so operators can smoke-test the endpoint.
        if request.url.path in ("/health", "/healthz"):
            return await call_next(request)

        expected = get_config().bearer_token
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            return JSONResponse({"error": "missing_bearer"}, status_code=401)
        if header.removeprefix("Bearer ").strip() != expected:
            return JSONResponse({"error": "invalid_bearer"}, status_code=401)
        return await call_next(request)
