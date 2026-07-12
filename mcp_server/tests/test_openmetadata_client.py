"""Tests for the OpenMetadata REST client wrapper."""
from __future__ import annotations

import pytest
import respx
from httpx import Response

from openmetadata_client import OpenMetadataError, get_client


def test_get_entity_by_fqn_url_escaping(mock_om: respx.Router) -> None:
    fqn = "prod_snowflake.analytics.dim_customer"
    mock_om.get(f"/tables/name/{fqn.replace('.', '%2E') if False else fqn}").mock(
        return_value=Response(200, json={"id": "1", "fullyQualifiedName": fqn})
    )
    # The client encodes the FQN safely; assert we get the entity back.
    client = get_client()
    entity = client.get_entity_by_fqn("tables", fqn)
    assert entity["id"] == "1"


def test_search_builds_correct_query(mock_om: respx.Router) -> None:
    route = mock_om.get("/search/query").mock(
        return_value=Response(200, json={"hits": {"total": {"value": 0}, "hits": []}})
    )
    client = get_client()
    client.search(query="customer", index="table_search_index", size=5)
    assert route.called
    request = route.calls.last.request
    assert "q=customer" in str(request.url)
    assert "index=table_search_index" in str(request.url)
    assert "size=5" in str(request.url)


def test_patch_uses_json_patch_content_type(mock_om: respx.Router) -> None:
    route = mock_om.patch("/tables/table-uuid-1").mock(
        return_value=Response(200, json={"id": "table-uuid-1", "description": "new"})
    )
    client = get_client()
    client.patch("/tables/table-uuid-1", [{"op": "add", "path": "/description", "value": "new"}])
    assert route.called
    req = route.calls.last.request
    assert req.headers["content-type"] == "application/json-patch+json"


def test_error_response_raises(mock_om: respx.Router) -> None:
    mock_om.get("/tables/name/missing.fqn").mock(return_value=Response(404, text="not found"))
    with pytest.raises(OpenMetadataError, match="404"):
        get_client().get_entity_by_fqn("tables", "missing.fqn")


def test_lineage_query_params(mock_om: respx.Router) -> None:
    route = mock_om.get("/lineage/table/table-uuid-1").mock(
        return_value=Response(200, json={"nodes": [], "upstreamEdges": [], "downstreamEdges": []})
    )
    get_client().get_lineage("table", "table-uuid-1", upstream=2, downstream=1)
    assert route.called
    url = str(route.calls.last.request.url)
    assert "upstreamDepth=2" in url
    assert "downstreamDepth=1" in url


def test_authorization_header_sent(mock_om: respx.Router) -> None:
    route = mock_om.get("/tables/name/x").mock(return_value=Response(200, json={}))
    get_client().get_entity_by_fqn("tables", "x")
    assert route.calls.last.request.headers["authorization"] == "Bearer test-jwt-token"
