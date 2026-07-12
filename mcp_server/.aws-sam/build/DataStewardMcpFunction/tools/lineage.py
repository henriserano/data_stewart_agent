"""Lineage: trace where data comes from and what depends on it."""
from __future__ import annotations

from typing import Any

from openmetadata_client import get_client


def _flatten_edges(lineage: dict[str, Any], direction: str) -> list[dict[str, Any]]:
    key = "upstreamEdges" if direction == "up" else "downstreamEdges"
    return lineage.get(key, []) or []


def _node_summary(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node.get("id"),
        "name": node.get("name") or node.get("displayName"),
        "fqn": node.get("fullyQualifiedName"),
        "type": node.get("type") or node.get("entityType"),
    }


def register(mcp) -> None:
    @mcp.tool()
    def get_upstream_lineage(fqn: str, entity_type: str = "tables", depth: int = 3) -> dict[str, Any]:
        """Return upstream lineage graph for an asset."""
        client = get_client()
        entity = client.get_entity_by_fqn(entity_type, fqn)
        singular = entity_type.rstrip("s")
        graph = client.get_lineage(singular, entity["id"], upstream_depth=depth, downstream_depth=0)
        return {
            "root": _node_summary(entity),
            "nodes": [_node_summary(n) for n in graph.get("nodes", [])],
            "edges": _flatten_edges(graph, "up"),
        }

    @mcp.tool()
    def get_downstream_lineage(fqn: str, entity_type: str = "tables", depth: int = 3) -> dict[str, Any]:
        """Return downstream lineage graph for an asset (what depends on it)."""
        client = get_client()
        entity = client.get_entity_by_fqn(entity_type, fqn)
        singular = entity_type.rstrip("s")
        graph = client.get_lineage(singular, entity["id"], upstream_depth=0, downstream_depth=depth)
        return {
            "root": _node_summary(entity),
            "nodes": [_node_summary(n) for n in graph.get("nodes", [])],
            "edges": _flatten_edges(graph, "down"),
        }

    @mcp.tool()
    def trace_to_source(fqn: str, entity_type: str = "tables", max_hops: int = 10) -> dict[str, Any]:
        """Walk upstream until no more parents are found. Returns the chain and any leaf roots (raw sources)."""
        client = get_client()
        entity = client.get_entity_by_fqn(entity_type, fqn)
        singular = entity_type.rstrip("s")
        graph = client.get_lineage(singular, entity["id"], upstream_depth=max_hops, downstream_depth=0)
        nodes_by_id = {n.get("id"): n for n in graph.get("nodes", [])}
        edges = graph.get("upstreamEdges", []) or []
        # A "root source" is a node that appears as a fromEntity but never as a toEntity in edges.
        to_ids = {e.get("toEntity") for e in edges}
        from_ids = {e.get("fromEntity") for e in edges}
        root_ids = from_ids - to_ids
        roots = [_node_summary(nodes_by_id[i]) for i in root_ids if i in nodes_by_id]
        return {
            "asset": _node_summary(entity),
            "rootSources": roots,
            "totalUpstreamNodes": len(nodes_by_id),
            "hops": len(edges),
        }

    @mcp.tool()
    def find_impact_scope(fqn: str, entity_type: str = "tables", depth: int = 5) -> dict[str, Any]:
        """List all downstream assets that would be affected by a change, with their owners."""
        client = get_client()
        entity = client.get_entity_by_fqn(entity_type, fqn)
        singular = entity_type.rstrip("s")
        graph = client.get_lineage(singular, entity["id"], upstream_depth=0, downstream_depth=depth)
        nodes = graph.get("nodes", []) or []
        # Enrich a few of the top-affected nodes with ownership.
        enriched: list[dict[str, Any]] = []
        for n in nodes[:50]:
            owners: list[str] = []
            try:
                node_type = (n.get("type") or "table") + "s"
                full = client.get_entity_by_id(node_type, n["id"], fields="owners")
                owners = [o.get("displayName") for o in full.get("owners", []) if o.get("displayName")]
            except Exception:
                pass
            enriched.append({**_node_summary(n), "owners": owners})
        return {"asset": _node_summary(entity), "impacted": enriched, "impactedCount": len(nodes)}

    @mcp.tool()
    def get_column_lineage(fqn: str) -> dict[str, Any]:
        """Return column-level lineage for a table, if the catalog captured it."""
        client = get_client()
        entity = client.get_entity_by_fqn("tables", fqn, fields="columns")
        graph = client.get_lineage("table", entity["id"], upstream_depth=2, downstream_depth=2)
        # OpenMetadata stores column-level mappings inside edge.columns
        col_edges: list[dict[str, Any]] = []
        for e in (graph.get("upstreamEdges", []) or []) + (graph.get("downstreamEdges", []) or []):
            cols = (e.get("lineageDetails") or {}).get("columnsLineage") or []
            for c in cols:
                col_edges.append({"from": c.get("fromColumns", []), "to": c.get("toColumn"), "sql": c.get("query")})
        return {"fqn": fqn, "columnEdges": col_edges}
