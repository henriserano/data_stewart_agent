"""Glossary and referentials: business terms, semantic alignment."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from openmetadata_client import get_client


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def register(mcp) -> None:
    @mcp.tool()
    def list_glossaries(limit: int = 50) -> dict[str, Any]:
        """List all business glossaries defined in the catalog."""
        resp = get_client().get("/glossaries", params={"limit": limit})
        return {"count": len(resp.get("data", [])), "glossaries": resp.get("data", [])}

    @mcp.tool()
    def list_glossary_terms(glossary_fqn: str | None = None, limit: int = 100) -> dict[str, Any]:
        """List glossary terms, optionally scoped to one glossary FQN."""
        params: dict[str, Any] = {"limit": limit, "fields": "children,parent,synonyms,relatedTerms"}
        if glossary_fqn:
            params["glossary"] = glossary_fqn
        resp = get_client().get("/glossaryTerms", params=params)
        return {"count": len(resp.get("data", [])), "terms": resp.get("data", [])}

    @mcp.tool()
    def get_glossary_term(fqn: str) -> dict[str, Any]:
        """Fetch a single glossary term by its fully-qualified name."""
        return get_client().get_entity_by_fqn(
            "glossaryTerms",
            fqn,
            fields="children,parent,synonyms,relatedTerms,reviewers,tags",
        )

    @mcp.tool()
    def search_glossary_terms(query: str, limit: int = 20) -> dict[str, Any]:
        """Full-text search over glossary terms."""
        resp = get_client().search(query=query or "*", index="glossary_term_search_index", size=limit)
        hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
        return {"count": len(hits), "terms": hits}

    @mcp.tool()
    def find_similar_terms(term_name: str, threshold: float = 0.75, limit: int = 200) -> dict[str, Any]:
        """Detect potential duplicates: terms with similar names across all glossaries.

        Use this to flag overlaps and consolidate referentials.
        """
        client = get_client()
        all_terms = client.get("/glossaryTerms", params={"limit": limit, "fields": "parent"}).get("data", [])
        matches: list[dict[str, Any]] = []
        for t in all_terms:
            name = t.get("name") or ""
            score = _similarity(term_name, name)
            if score >= threshold and name.lower() != term_name.lower():
                matches.append({
                    "fqn": t.get("fullyQualifiedName"),
                    "name": name,
                    "glossary": (t.get("parent") or {}).get("fullyQualifiedName"),
                    "similarity": round(score, 3),
                })
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return {"query": term_name, "threshold": threshold, "matches": matches}

    @mcp.tool()
    def link_asset_to_term(
        asset_fqn: str,
        term_fqn: str,
        entity_type: str = "tables",
        confirm: bool = False,
    ) -> dict[str, Any]:
        """Attach a glossary term as a tag on an asset. Requires confirm=True to write."""
        client = get_client()
        entity = client.get_entity_by_fqn(entity_type, asset_fqn, fields="tags")
        current_tags = entity.get("tags", []) or []
        if any(t.get("tagFQN") == term_fqn for t in current_tags):
            return {"applied": False, "reason": "Term already linked."}
        new_tags = current_tags + [{"tagFQN": term_fqn, "source": "Glossary", "labelType": "Manual", "state": "Confirmed"}]
        patch = [{"op": "replace" if current_tags else "add", "path": "/tags", "value": new_tags}]
        if not confirm:
            return {"applied": False, "dryRun": True, "patch": patch}
        client.patch(f"/{entity_type}/{entity['id']}", patch)
        return {"applied": True, "asset": asset_fqn, "term": term_fqn}

    @mcp.tool()
    def list_assets_linked_to_term(term_fqn: str, limit: int = 50) -> dict[str, Any]:
        """List assets tagged with a given glossary term."""
        resp = get_client().search(
            query=f'tags.tagFQN:"{term_fqn}"',
            index="table_search_index",
            size=limit,
        )
        hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
        return {"term": term_fqn, "count": len(hits), "assets": hits}
