"""Documentation: propose and apply descriptions on assets and their columns."""
from __future__ import annotations

from typing import Any

from openmetadata_client import get_client


def _get_table(fqn: str) -> dict[str, Any]:
    return get_client().get_entity_by_fqn("tables", fqn, fields="columns,description")


def register(mcp) -> None:
    @mcp.tool()
    def get_asset_description(fqn: str, entity_type: str = "tables") -> dict[str, Any]:
        """Return the current description of an asset."""
        entity = get_client().get_entity_by_fqn(entity_type, fqn)
        return {
            "fqn": entity.get("fullyQualifiedName"),
            "description": entity.get("description"),
            "hasDescription": bool(entity.get("description")),
        }

    @mcp.tool()
    def get_column_descriptions(fqn: str) -> dict[str, Any]:
        """Return per-column descriptions for a table."""
        entity = _get_table(fqn)
        return {
            "fqn": entity.get("fullyQualifiedName"),
            "columns": [
                {"name": c.get("name"), "description": c.get("description")}
                for c in entity.get("columns", [])
            ],
        }

    @mcp.tool()
    def propose_asset_description(fqn: str, description: str, entity_type: str = "tables") -> dict[str, Any]:
        """Dry-run: return the JSON Patch that would update the asset description. Nothing is written.

        Follow up with apply_asset_description(confirm=True) to persist.
        """
        entity = get_client().get_entity_by_fqn(entity_type, fqn)
        patch = [{"op": "add", "path": "/description", "value": description}]
        return {
            "fqn": fqn,
            "entityId": entity.get("id"),
            "before": entity.get("description"),
            "after": description,
            "patch": patch,
            "dryRun": True,
        }

    @mcp.tool()
    def apply_asset_description(
        fqn: str,
        description: str,
        confirm: bool = False,
        entity_type: str = "tables",
    ) -> dict[str, Any]:
        """Apply a new description on an asset. Requires confirm=True to actually PATCH."""
        if not confirm:
            return {"applied": False, "reason": "confirm must be True to write to the catalog."}
        client = get_client()
        entity = client.get_entity_by_fqn(entity_type, fqn)
        patch = [{"op": "add", "path": "/description", "value": description}]
        client.patch(f"/{entity_type}/{entity['id']}", patch)
        return {"applied": True, "fqn": fqn, "description": description}

    @mcp.tool()
    def propose_column_descriptions(fqn: str, columns: dict[str, str]) -> dict[str, Any]:
        """Dry-run: build the JSON Patch that would update per-column descriptions.

        Args:
            fqn: Table FQN.
            columns: mapping {"column_name": "proposed description", ...}
        """
        entity = _get_table(fqn)
        current = {c["name"]: c for c in entity.get("columns", [])}
        patch: list[dict[str, Any]] = []
        diff: list[dict[str, Any]] = []
        for name, new_desc in columns.items():
            if name not in current:
                diff.append({"column": name, "status": "not_found"})
                continue
            idx = next(i for i, c in enumerate(entity["columns"]) if c["name"] == name)
            op = "add" if not current[name].get("description") else "replace"
            patch.append({"op": op, "path": f"/columns/{idx}/description", "value": new_desc})
            diff.append({"column": name, "before": current[name].get("description"), "after": new_desc})
        return {"fqn": fqn, "entityId": entity.get("id"), "diff": diff, "patch": patch, "dryRun": True}

    @mcp.tool()
    def apply_column_descriptions(fqn: str, columns: dict[str, str], confirm: bool = False) -> dict[str, Any]:
        """Apply per-column descriptions. Requires confirm=True."""
        if not confirm:
            return {"applied": False, "reason": "confirm must be True to write to the catalog."}
        client = get_client()
        entity = _get_table(fqn)
        current = {c["name"]: (i, c) for i, c in enumerate(entity.get("columns", []))}
        patch: list[dict[str, Any]] = []
        for name, new_desc in columns.items():
            if name not in current:
                continue
            idx, col = current[name]
            op = "add" if not col.get("description") else "replace"
            patch.append({"op": op, "path": f"/columns/{idx}/description", "value": new_desc})
        if not patch:
            return {"applied": False, "reason": "No matching columns found."}
        client.patch(f"/tables/{entity['id']}", patch)
        return {"applied": True, "fqn": fqn, "columnsUpdated": len(patch)}
