"""Shared test fixtures.

The MCP server tools are registered as closures inside module-level ``register(mcp)``
functions. To exercise them from tests without spinning up an MCP transport, we
register them onto a real ``FastMCP`` instance and pull each tool's underlying
callable back out of the registry.
"""
from __future__ import annotations

import os
from typing import Any, Callable

import pytest
import respx
from httpx import Response
from mcp.server.fastmcp import FastMCP

# Env vars must be set before importing anything that reads config.
os.environ.setdefault("OPENMETADATA_HOST", "https://openmetadata.test")
os.environ.setdefault("OPENMETADATA_JWT", "test-jwt-token")
os.environ.setdefault("MCP_BEARER_TOKEN", "test-bearer")

from src import openmetadata_client  # noqa: E402
from src.tools import (  # noqa: E402
    discovery,
    documentation,
    glossary,
    golden_source,
    governance,
    lineage,
    quality,
)

TOOL_MODULES = {
    "discovery": discovery,
    "documentation": documentation,
    "glossary": glossary,
    "golden_source": golden_source,
    "governance": governance,
    "lineage": lineage,
    "quality": quality,
}


@pytest.fixture(autouse=True)
def _reset_client_cache() -> None:
    """Force a fresh OpenMetadataClient per test so respx routing is deterministic."""
    openmetadata_client.get_client.cache_clear()
    yield
    openmetadata_client.get_client.cache_clear()


@pytest.fixture
def mock_om() -> respx.Router:
    """Give tests a respx router mounted on the test OpenMetadata host."""
    with respx.mock(base_url="https://openmetadata.test/api/v1", assert_all_called=False) as router:
        yield router


@pytest.fixture
def tools() -> dict[str, Callable[..., Any]]:
    """Return a flat dict {tool_name: callable} across all modules.

    FastMCP stores registered tools on ``mcp._tool_manager._tools``; we introspect
    that structure to hand back the wrapped functions for direct invocation.
    """
    mcp = FastMCP("test-data-steward")
    for module in TOOL_MODULES.values():
        module.register(mcp)
    # FastMCP internal API: _tool_manager.list_tools() returns Tool objects
    # each of which has a .fn attribute pointing at the underlying callable.
    registry: dict[str, Callable[..., Any]] = {}
    for tool in mcp._tool_manager.list_tools():
        registry[tool.name] = tool.fn
    return registry


# -------------------------------------------------------- sample OpenMetadata payloads

@pytest.fixture
def sample_table() -> dict[str, Any]:
    return {
        "id": "table-uuid-1",
        "name": "dim_customer",
        "fullyQualifiedName": "prod_snowflake.analytics.dim_customer",
        "description": "Customer dimension.",
        "owners": [{"id": "team-1", "type": "team", "displayName": "Data Platform"}],
        "columns": [
            {"name": "customer_id", "dataType": "BIGINT", "description": "Customer surrogate key.", "tags": []},
            {"name": "email", "dataType": "VARCHAR", "description": None, "tags": [{"tagFQN": "PII.Email"}]},
            {"name": "created_at", "dataType": "TIMESTAMP", "description": "Row creation timestamp.", "tags": []},
        ],
        "tier": {"tagFQN": "Tier.Tier1"},
        "usageSummary": {"weeklyStats": {"count": 250}},
        "tags": [],
    }


@pytest.fixture
def sample_search_response(sample_table: dict[str, Any]) -> dict[str, Any]:
    return {
        "hits": {
            "total": {"value": 1},
            "hits": [{"_source": sample_table}],
        }
    }


@pytest.fixture
def sample_lineage() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "raw-1", "name": "raw_customer", "fullyQualifiedName": "raw_snowflake.stg.raw_customer", "type": "table"},
            {"id": "table-uuid-1", "name": "dim_customer", "fullyQualifiedName": "prod_snowflake.analytics.dim_customer", "type": "table"},
        ],
        "upstreamEdges": [
            {"fromEntity": "raw-1", "toEntity": "table-uuid-1"},
        ],
        "downstreamEdges": [],
    }
