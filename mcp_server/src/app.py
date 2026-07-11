from mcp.server.fastmcp import FastMCP
from mangum import Mangum
from starlette.responses import JSONResponse
from starlette.routing import Route

from .auth import BearerAuthMiddleware
from .tools import (
    discovery,
    documentation,
    glossary,
    golden_source,
    governance,
    lineage,
    quality,
)

mcp = FastMCP("data-steward", instructions=(
    "MCP server for a Data Steward assistant. Exposes read/write metadata operations "
    "on an OpenMetadata catalog. Write operations require confirm=True to actually apply; "
    "otherwise they return a dry-run diff for review."
))

for module in (discovery, documentation, lineage, glossary, golden_source, quality, governance):
    module.register(mcp)


async def _healthcheck(_request):
    return JSONResponse({"status": "ok", "server": "data-steward"})


asgi_app = mcp.streamable_http_app()
asgi_app.add_middleware(BearerAuthMiddleware)
asgi_app.router.routes.append(Route("/health", _healthcheck))

handler = Mangum(asgi_app, lifespan="off")
