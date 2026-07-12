from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest
import respx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Force test env — overrides anything the shell may have exported via `source .env`.
os.environ["OPENMETADATA_HOST"] = "https://openmetadata.test"
os.environ["OPENMETADATA_JWT"] = "test-jwt-token"
os.environ["MCP_BEARER_TOKEN"] = "test-bearer"

import config  # noqa: E402
import openmetadata_client  # noqa: E402
from tools import TOOLS  # noqa: E402 — importing registers all tools


@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    config._CONFIG = None
    openmetadata_client._CLIENT = None
    yield
    config._CONFIG = None
    openmetadata_client._CLIENT = None


@pytest.fixture
def mock_om() -> respx.Router:
    with respx.mock(base_url="https://openmetadata.test/api/v1", assert_all_called=False) as router:
        yield router


@pytest.fixture
def tools() -> dict[str, Any]:
    """Flat dict {tool_name: callable}."""
    return {name: spec["fn"] for name, spec in TOOLS.items()}


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
    return {"hits": {"total": {"value": 1}, "hits": [{"_source": sample_table}]}}


@pytest.fixture
def sample_lineage() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "raw-1", "name": "raw_customer", "fullyQualifiedName": "raw_snowflake.stg.raw_customer", "type": "table"},
            {"id": "table-uuid-1", "name": "dim_customer", "fullyQualifiedName": "prod_snowflake.analytics.dim_customer", "type": "table"},
        ],
        "upstreamEdges": [{"fromEntity": "raw-1", "toEntity": "table-uuid-1"}],
        "downstreamEdges": [],
    }
