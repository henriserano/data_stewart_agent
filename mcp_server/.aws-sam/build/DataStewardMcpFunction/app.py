"""Lambda-native MCP server.

Speaks JSON-RPC 2.0 directly over Lambda Function URL (BUFFERED). No ASGI framework,
no session manager, no LWA. Everything is stateless per request.

Routes:
    GET  /health  → liveness (no auth)
    POST /mcp     → JSON-RPC 2.0 (bearer required)
"""
from __future__ import annotations

import base64
import json
import traceback
from typing import Any

from config import get_config
from tools import TOOLS

SERVER_INFO = {"name": "data-steward", "version": "0.2.0"}
PROTOCOL_VERSION = "2024-11-05"


# --------------------------------------------------------------------- helpers

def _json(status: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _rpc_ok(req_id: Any, result: Any) -> dict[str, Any]:
    return _json(200, {"jsonrpc": "2.0", "id": req_id, "result": result})


def _rpc_err(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return _json(200, {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


def _extract_body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    return json.loads(raw) if raw else {}


def _check_bearer(headers: dict[str, str]) -> bool:
    expected = get_config().bearer_token
    auth = headers.get("authorization") or headers.get("Authorization") or ""
    return auth.startswith("Bearer ") and auth[7:].strip() == expected


# --------------------------------------------------------------------- MCP methods

def _handle_initialize() -> dict[str, Any]:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {"listChanged": False}},
        "serverInfo": SERVER_INFO,
        "instructions": (
            "Data Steward MCP server on top of OpenMetadata. Write tools require confirm=True; "
            "otherwise they return a dry-run JSON Patch."
        ),
    }


def _handle_tools_list() -> dict[str, Any]:
    return {
        "tools": [
            {"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"]}
            for name, spec in TOOLS.items()
        ]
    }


def _handle_tools_call(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    args = params.get("arguments") or {}
    data = TOOLS[name]["fn"](**args)
    return {"content": [{"type": "text", "text": json.dumps(data, default=str)}]}


# --------------------------------------------------------------------- Lambda entrypoint

def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    method_http = (event.get("requestContext", {}).get("http", {}).get("method")
                   or event.get("httpMethod") or "GET")
    path = event.get("rawPath") or event.get("path") or "/"
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}

    # Health probe — no auth
    if path.rstrip("/") == "/health":
        return _json(200, {"status": "ok", "server": SERVER_INFO["name"], "tools": len(TOOLS)})

    # Everything else needs bearer
    if not _check_bearer(headers):
        return _json(401, {"error": "unauthorized"})

    if method_http != "POST" or not path.rstrip("/").endswith("/mcp"):
        return _json(404, {"error": "not_found"})

    body = _extract_body(event)
    req_id = body.get("id")
    rpc_method = body.get("method")

    # Notifications (no id) — no response body expected.
    if req_id is None and rpc_method and rpc_method.startswith("notifications/"):
        return {"statusCode": 202, "headers": {"Content-Type": "application/json"}, "body": ""}

    try:
        if rpc_method == "initialize":
            return _rpc_ok(req_id, _handle_initialize())
        if rpc_method == "tools/list":
            return _rpc_ok(req_id, _handle_tools_list())
        if rpc_method == "tools/call":
            return _rpc_ok(req_id, _handle_tools_call(body.get("params") or {}))
        return _rpc_err(req_id, -32601, f"method not found: {rpc_method}")
    except Exception as e:
        return _rpc_err(req_id, -32000, f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")
