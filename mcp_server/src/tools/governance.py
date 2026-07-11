"""Governance: ownership, domains, teams, orphaned assets."""
from __future__ import annotations

from typing import Any

from ..openmetadata_client import get_client


def register(mcp) -> None:
    @mcp.tool()
    def get_asset_owner(fqn: str, entity_type: str = "tables") -> dict[str, Any]:
        """Return the current owner(s) of an asset."""
        entity = get_client().get_entity_by_fqn(entity_type, fqn, fields="owners")
        owners = entity.get("owners") or []
        return {
            "fqn": fqn,
            "owners": [{"name": o.get("displayName"), "type": o.get("type"), "id": o.get("id")} for o in owners],
            "hasOwner": bool(owners),
        }

    @mcp.tool()
    def list_orphan_assets(entity_type: str = "table", limit: int = 50) -> dict[str, Any]:
        """List assets without any owner (governance backlog)."""
        resp = get_client().search(
            query="NOT owners.name:*",
            index=f"{entity_type}_search_index",
            size=limit,
        )
        hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
        return {"count": len(hits), "assets": hits}

    @mcp.tool()
    def propose_ownership(
        fqn: str,
        owner_name: str,
        owner_type: str = "team",
        confirm: bool = False,
        entity_type: str = "tables",
    ) -> dict[str, Any]:
        """Assign a user or team as owner. Requires confirm=True.

        Args:
            owner_type: "user" or "team".
        """
        client = get_client()
        entity = client.get_entity_by_fqn(entity_type, fqn, fields="owners")
        # Resolve the owner reference by name.
        endpoint = "teams" if owner_type == "team" else "users"
        owner = client.get_entity_by_fqn(endpoint, owner_name)
        new_owner = {"id": owner["id"], "type": owner_type, "name": owner.get("name")}
        patch = [{"op": "add", "path": "/owners", "value": [new_owner]}]
        if not confirm:
            return {"applied": False, "dryRun": True, "patch": patch}
        client.patch(f"/{entity_type}/{entity['id']}", patch)
        return {"applied": True, "fqn": fqn, "owner": owner_name}

    @mcp.tool()
    def list_teams(limit: int = 100) -> dict[str, Any]:
        """List teams defined in the catalog."""
        resp = get_client().get("/teams", params={"limit": limit})
        return {"count": len(resp.get("data", [])), "teams": resp.get("data", [])}

    @mcp.tool()
    def list_domains(limit: int = 100) -> dict[str, Any]:
        """List business domains defined in the catalog."""
        resp = get_client().get("/domains", params={"limit": limit})
        return {"count": len(resp.get("data", [])), "domains": resp.get("data", [])}

    @mcp.tool()
    def get_stewardship_dashboard(owner_name: str) -> dict[str, Any]:
        """One-shot snapshot of everything an owner is responsible for and its health signals."""
        client = get_client()
        owned = client.search(
            query=f'owners.displayName:"{owner_name}"',
            index="table_search_index",
            size=200,
        )
        hits = [h["_source"] for h in owned.get("hits", {}).get("hits", [])]
        undocumented = [h for h in hits if not h.get("description")]
        no_tests = [h for h in hits if not h.get("testSuite")]
        no_tier = [h for h in hits if not (h.get("tier") or {}).get("tagFQN")]
        return {
            "owner": owner_name,
            "assetCount": len(hits),
            "undocumentedCount": len(undocumented),
            "noTestsCount": len(no_tests),
            "noTierCount": len(no_tier),
            "undocumented": [{"fqn": h.get("fullyQualifiedName")} for h in undocumented[:20]],
            "noTests": [{"fqn": h.get("fullyQualifiedName")} for h in no_tests[:20]],
        }
