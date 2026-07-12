"""Discovery: search, list, and inspect assets in the catalog."""
from __future__ import annotations

from typing import Any

from openmetadata_client import get_client

ENTITY_INDEX = {
    "table": "table_search_index",
    "database": "database_search_index",
    "databaseSchema": "database_schema_search_index",
    "dashboard": "dashboard_search_index",
    "pipeline": "pipeline_search_index",
    "topic": "topic_search_index",
    "mlmodel": "mlmodel_search_index",
    "container": "container_search_index",
    "glossaryTerm": "glossary_term_search_index",
}


def _index_for(entity_type: str) -> str:
    return ENTITY_INDEX.get(entity_type, f"{entity_type}_search_index")


def _hits(search_response: dict[str, Any]) -> list[dict[str, Any]]:
    return [h["_source"] for h in search_response.get("hits", {}).get("hits", [])]


def register(mcp) -> None:
    @mcp.tool()
    def search_assets(
        query: str,
        entity_type: str = "table",
        limit: int = 20,
        owner: str | None = None,
        tag: str | None = None,
    ) -> dict[str, Any]:
        """Full-text search across the catalog.

        Args:
            query: Search string. Use "*" for a broad listing.
            entity_type: table, dashboard, pipeline, topic, mlmodel, container, glossaryTerm.
            limit: Max results (default 20).
            owner: Optional owner name (user or team) to filter by.
            tag: Optional tag FQN to filter by (e.g. "PII.Sensitive").
        """
        filters: list[str] = []
        if owner:
            filters.append(f'"owners.displayName":"{owner}"')
        if tag:
            filters.append(f'"tags.tagFQN":"{tag}"')
        query_string = query
        if filters:
            query_string = f"{query} AND " + " AND ".join(filters) if query and query != "*" else " AND ".join(filters)
        resp = get_client().search(query=query_string, index=_index_for(entity_type), size=limit)
        return {"total": resp.get("hits", {}).get("total", {}).get("value", 0), "results": _hits(resp)}

    @mcp.tool()
    def get_asset(fqn: str, entity_type: str = "tables") -> dict[str, Any]:
        """Fetch full metadata for one asset by its fully-qualified name.

        Args:
            fqn: e.g. "prod_snowflake.analytics.dim_customer".
            entity_type: plural form of the entity endpoint (tables, dashboards, pipelines, topics, mlmodels, containers).
        """
        return get_client().get_entity_by_fqn(
            entity_type,
            fqn,
            fields="owners,tags,columns,description,followers,domain,dataProducts,tier,usageSummary",
        )

    @mcp.tool()
    def get_asset_schema(fqn: str) -> dict[str, Any]:
        """Return only the columns/schema of a table with their descriptions and types."""
        entity = get_client().get_entity_by_fqn("tables", fqn, fields="columns,description")
        return {
            "fqn": entity.get("fullyQualifiedName"),
            "description": entity.get("description"),
            "columns": [
                {
                    "name": c.get("name"),
                    "dataType": c.get("dataType"),
                    "description": c.get("description"),
                    "tags": [t.get("tagFQN") for t in c.get("tags", [])],
                }
                for c in entity.get("columns", [])
            ],
        }

    @mcp.tool()
    def list_assets_by_owner(
        owner_name: str,
        entity_type: str = "table",
        limit: int = 50,
    ) -> dict[str, Any]:
        """List assets owned by a given user or team display name."""
        resp = get_client().search(
            query=f'owners.displayName:"{owner_name}"',
            index=_index_for(entity_type),
            size=limit,
        )
        return {"owner": owner_name, "count": len(_hits(resp)), "assets": _hits(resp)}

    @mcp.tool()
    def list_undocumented_assets(
        entity_type: str = "table",
        owner_name: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List assets missing a description (documentation backlog).

        Args:
            entity_type: table, dashboard, pipeline, etc.
            owner_name: Optional owner filter.
            limit: Max results.
        """
        parts = ["NOT description:*"]
        if owner_name:
            parts.append(f'owners.displayName:"{owner_name}"')
        resp = get_client().search(
            query=" AND ".join(parts),
            index=_index_for(entity_type),
            size=limit,
        )
        assets = [
            {"fqn": h.get("fullyQualifiedName"), "name": h.get("name"), "owners": h.get("owners", [])}
            for h in _hits(resp)
        ]
        return {"count": len(assets), "assets": assets}

    @mcp.tool()
    def list_assets_by_domain(domain_fqn: str, entity_type: str = "table", limit: int = 50) -> dict[str, Any]:
        """List assets attached to a business Domain."""
        resp = get_client().search(
            query=f'domain.fullyQualifiedName:"{domain_fqn}"',
            index=_index_for(entity_type),
            size=limit,
        )
        return {"domain": domain_fqn, "count": len(_hits(resp)), "assets": _hits(resp)}

    @mcp.tool()
    def list_assets_by_tag(tag_fqn: str, entity_type: str = "table", limit: int = 50) -> dict[str, Any]:
        """List assets carrying a given Classification tag (e.g. PII.Sensitive)."""
        resp = get_client().search(
            query=f'tags.tagFQN:"{tag_fqn}"',
            index=_index_for(entity_type),
            size=limit,
        )
        return {"tag": tag_fqn, "count": len(_hits(resp)), "assets": _hits(resp)}
