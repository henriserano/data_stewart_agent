"""Lineage: trace data origin and impact."""
from __future__ import annotations

from typing import Any

from openmetadata_client import get_client
from tools._registry import tool


def _node_summary(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node.get("id"),
        "name": node.get("name") or node.get("displayName"),
        "fqn": node.get("fullyQualifiedName"),
        "type": node.get("type") or node.get("entityType"),
    }


@tool
def get_upstream_lineage(fqn: str, entity_type: str = "tables", depth: int = 3) -> dict[str, Any]:
    """Return upstream lineage graph for an asset."""
    client = get_client()
    entity = client.get_entity_by_fqn(entity_type, fqn)
    graph = client.get_lineage(entity_type.rstrip("s"), entity["id"], upstream=depth, downstream=0)
    return {
        "root": _node_summary(entity),
        "nodes": [_node_summary(n) for n in graph.get("nodes", [])],
        "edges": graph.get("upstreamEdges", []),
    }


@tool
def get_downstream_lineage(fqn: str, entity_type: str = "tables", depth: int = 3) -> dict[str, Any]:
    """Return downstream lineage graph for an asset."""
    client = get_client()
    entity = client.get_entity_by_fqn(entity_type, fqn)
    graph = client.get_lineage(entity_type.rstrip("s"), entity["id"], upstream=0, downstream=depth)
    return {
        "root": _node_summary(entity),
        "nodes": [_node_summary(n) for n in graph.get("nodes", [])],
        "edges": graph.get("downstreamEdges", []),
    }


@tool
def trace_to_source(fqn: str, entity_type: str = "tables", max_hops: int = 10) -> dict[str, Any]:
    """Walk upstream until no more parents. Returns root sources of the chain."""
    client = get_client()
    entity = client.get_entity_by_fqn(entity_type, fqn)
    graph = client.get_lineage(entity_type.rstrip("s"), entity["id"], upstream=max_hops, downstream=0)
    nodes_by_id = {n.get("id"): n for n in graph.get("nodes", [])}
    edges = graph.get("upstreamEdges", []) or []
    to_ids = {e.get("toEntity") for e in edges}
    root_ids = {e.get("fromEntity") for e in edges} - to_ids
    return {
        "asset": _node_summary(entity),
        "rootSources": [_node_summary(nodes_by_id[i]) for i in root_ids if i in nodes_by_id],
        "totalUpstreamNodes": len(nodes_by_id),
        "hops": len(edges),
    }


@tool
def find_impact_scope(fqn: str, entity_type: str = "tables", depth: int = 5) -> dict[str, Any]:
    """Downstream impact scope: nodes affected by a change. Fast — no per-node enrichment."""
    client = get_client()
    entity = client.get_entity_by_fqn(entity_type, fqn)
    graph = client.get_lineage(entity_type.rstrip("s"), entity["id"], upstream=0, downstream=depth)
    nodes = graph.get("nodes", []) or []
    return {
        "asset": _node_summary(entity),
        "impacted": [_node_summary(n) for n in nodes],
        "impactedCount": len(nodes),
    }


@tool
def get_column_lineage(fqn: str) -> dict[str, Any]:
    """Return column-level lineage for a table, if the catalog captured it."""
    client = get_client()
    entity = client.get_entity_by_fqn("tables", fqn, fields="columns")
    graph = client.get_lineage("table", entity["id"], upstream=2, downstream=2)
    col_edges: list[dict[str, Any]] = []
    for e in (graph.get("upstreamEdges", []) or []) + (graph.get("downstreamEdges", []) or []):
        for c in (e.get("lineageDetails") or {}).get("columnsLineage") or []:
            col_edges.append({"from": c.get("fromColumns", []), "to": c.get("toColumn"), "sql": c.get("query")})
    return {"fqn": fqn, "columnEdges": col_edges}
