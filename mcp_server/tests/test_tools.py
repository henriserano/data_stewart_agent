"""Smoke and behavior tests across the 7 tool modules.

Each test drives one tool through respx-mocked OpenMetadata endpoints and
asserts the shape/semantics of the output.
"""
from __future__ import annotations

from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

import respx
from httpx import Response


def _search_response(sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {"hits": {"total": {"value": len(sources)}, "hits": [{"_source": s} for s in sources]}}


# ------------------------------------------------------------------ discovery

def test_search_assets_returns_normalized_shape(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
    sample_search_response: dict[str, Any],
) -> None:
    mock_om.get("/search/query").mock(return_value=Response(200, json=sample_search_response))
    result = tools["search_assets"](query="customer", entity_type="table", limit=10)
    assert result["total"] == 1
    assert result["results"][0]["name"] == "dim_customer"


def test_get_asset_schema_extracts_columns(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
    sample_table: dict[str, Any],
) -> None:
    mock_om.get(f"/tables/name/{sample_table['fullyQualifiedName']}").mock(
        return_value=Response(200, json=sample_table)
    )
    schema = tools["get_asset_schema"](fqn=sample_table["fullyQualifiedName"])
    assert schema["fqn"] == sample_table["fullyQualifiedName"]
    assert len(schema["columns"]) == 3
    assert schema["columns"][1]["tags"] == ["PII.Email"]


def test_list_undocumented_assets_uses_missing_desc_filter(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
) -> None:
    undocumented = {"fullyQualifiedName": "prod.stg.raw_events", "name": "raw_events", "owners": []}
    route = mock_om.get("/search/query").mock(return_value=Response(200, json=_search_response([undocumented])))
    result = tools["list_undocumented_assets"](entity_type="table", limit=10)
    assert result["count"] == 1
    query = parse_qs(urlparse(str(route.calls.last.request.url)).query)
    assert query["q"] == ["NOT description:*"]


# ------------------------------------------------------------------ documentation

def test_propose_asset_description_is_dry_run(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
    sample_table: dict[str, Any],
) -> None:
    fqn = sample_table["fullyQualifiedName"]
    mock_om.get(f"/tables/name/{fqn}").mock(return_value=Response(200, json=sample_table))
    result = tools["propose_asset_description"](fqn=fqn, description="New description")
    assert result["dryRun"] is True
    assert result["after"] == "New description"
    assert result["patch"][0] == {"op": "add", "path": "/description", "value": "New description"}


def test_apply_asset_description_requires_confirm(
    tools: dict[str, Callable[..., Any]],
    sample_table: dict[str, Any],
) -> None:
    # confirm=False must short-circuit before any HTTP call.
    result = tools["apply_asset_description"](fqn=sample_table["fullyQualifiedName"], description="X", confirm=False)
    assert result["applied"] is False


def test_apply_asset_description_writes_when_confirmed(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
    sample_table: dict[str, Any],
) -> None:
    fqn = sample_table["fullyQualifiedName"]
    mock_om.get(f"/tables/name/{fqn}").mock(return_value=Response(200, json=sample_table))
    patch_route = mock_om.patch(f"/tables/{sample_table['id']}").mock(
        return_value=Response(200, json={"id": sample_table["id"]})
    )
    result = tools["apply_asset_description"](fqn=fqn, description="New", confirm=True)
    assert result["applied"] is True
    assert patch_route.called


def test_propose_column_descriptions_diffs_correctly(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
    sample_table: dict[str, Any],
) -> None:
    fqn = sample_table["fullyQualifiedName"]
    mock_om.get(f"/tables/name/{fqn}").mock(return_value=Response(200, json=sample_table))
    proposal = {"email": "Customer email address (PII).", "unknown_col": "Ignored."}
    result = tools["propose_column_descriptions"](fqn=fqn, columns=proposal)
    diff_by_col = {d["column"]: d for d in result["diff"]}
    assert diff_by_col["email"]["before"] is None
    assert diff_by_col["email"]["after"] == "Customer email address (PII)."
    assert diff_by_col["unknown_col"]["status"] == "not_found"
    # One patch op for email, none for unknown_col
    assert len(result["patch"]) == 1


# ------------------------------------------------------------------ lineage

def test_trace_to_source_finds_root(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
    sample_table: dict[str, Any],
    sample_lineage: dict[str, Any],
) -> None:
    fqn = sample_table["fullyQualifiedName"]
    mock_om.get(f"/tables/name/{fqn}").mock(return_value=Response(200, json=sample_table))
    mock_om.get(f"/lineage/table/{sample_table['id']}").mock(
        return_value=Response(200, json=sample_lineage)
    )
    result = tools["trace_to_source"](fqn=fqn, max_hops=5)
    assert len(result["rootSources"]) == 1
    assert result["rootSources"][0]["fqn"] == "raw_snowflake.stg.raw_customer"


def test_find_impact_scope_returns_count(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
    sample_table: dict[str, Any],
    sample_lineage: dict[str, Any],
) -> None:
    fqn = sample_table["fullyQualifiedName"]
    mock_om.get(f"/tables/name/{fqn}").mock(return_value=Response(200, json=sample_table))
    mock_om.get(f"/lineage/table/{sample_table['id']}").mock(
        return_value=Response(200, json={"nodes": sample_lineage["nodes"], "downstreamEdges": [], "upstreamEdges": []})
    )
    result = tools["find_impact_scope"](fqn=fqn, depth=3)
    assert result["impactedCount"] == 2


# ------------------------------------------------------------------ glossary

def test_find_similar_terms_ranks_by_similarity(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
) -> None:
    terms_response = {
        "data": [
            {"name": "Customer", "fullyQualifiedName": "sales.Customer", "parent": {"fullyQualifiedName": "sales"}},
            {"name": "Customers", "fullyQualifiedName": "finance.Customers", "parent": {"fullyQualifiedName": "finance"}},
            {"name": "Product", "fullyQualifiedName": "supply.Product", "parent": {"fullyQualifiedName": "supply"}},
        ]
    }
    mock_om.get("/glossaryTerms").mock(return_value=Response(200, json=terms_response))
    result = tools["find_similar_terms"](term_name="customer", threshold=0.6)
    names = [m["name"] for m in result["matches"]]
    assert "Customers" in names
    assert "Product" not in names


# ------------------------------------------------------------------ golden_source

def test_assess_source_quality_scores_signals(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
    sample_table: dict[str, Any],
) -> None:
    # Enrich the sample with a test suite to boost the score.
    enriched = {**sample_table, "testSuite": {"id": "ts-1"}, "profile": {"timestamp": 1700000000}}
    fqn = enriched["fullyQualifiedName"]
    mock_om.get(f"/tables/name/{fqn}").mock(return_value=Response(200, json=enriched))
    result = tools["assess_source_quality"](fqn=fqn)
    # owner + description + Tier1 + weekly>100 + profile + testSuite = 20+15+20+15+10+15 = 95
    assert result["score"] >= 90
    assert result["signals"]["hasTestSuite"] is True


# ------------------------------------------------------------------ quality

def test_suggest_test_cases_generates_rules_from_schema(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
    sample_table: dict[str, Any],
) -> None:
    fqn = sample_table["fullyQualifiedName"]
    mock_om.get(f"/tables/name/{fqn}").mock(return_value=Response(200, json=sample_table))
    result = tools["suggest_test_cases"](fqn=fqn)
    suggestions = result["suggestions"]
    # customer_id should get a uniqueness suggestion (ends with _id)
    unique_on_id = any(s["column"] == "customer_id" and s["testDefinition"] == "columnValuesToBeUnique" for s in suggestions)
    assert unique_on_id
    # email (VARCHAR) should get not-null + length rules
    email_rules = {s["testDefinition"] for s in suggestions if s["column"] == "email"}
    assert "columnValuesToNotBeNull" in email_rules


# ------------------------------------------------------------------ governance

def test_get_stewardship_dashboard_aggregates(
    tools: dict[str, Callable[..., Any]],
    mock_om: respx.Router,
) -> None:
    assets = [
        {"fullyQualifiedName": "a.b.t1", "description": "ok", "testSuite": {"id": "ts"}, "tier": {"tagFQN": "Tier.Tier1"}},
        {"fullyQualifiedName": "a.b.t2", "description": None, "testSuite": None, "tier": {}},
        {"fullyQualifiedName": "a.b.t3", "description": None, "testSuite": None, "tier": {}},
    ]
    mock_om.get("/search/query").mock(return_value=Response(200, json=_search_response(assets)))
    result = tools["get_stewardship_dashboard"](owner_name="Data Platform")
    assert result["assetCount"] == 3
    assert result["undocumentedCount"] == 2
    assert result["noTestsCount"] == 2
    assert result["noTierCount"] == 2
