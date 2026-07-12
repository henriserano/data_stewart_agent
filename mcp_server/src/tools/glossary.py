"""Glossary and referentials."""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from openmetadata_client import get_client
from tools._registry import tool


@tool
def list_glossaries(limit: int = 50) -> dict[str, Any]:
    """List all business glossaries."""
    resp = get_client().get("/glossaries", params={"limit": limit})
    return {"count": len(resp.get("data", [])), "glossaries": resp.get("data", [])}


@tool
def list_glossary_terms(glossary_fqn: str | None = None, limit: int = 100) -> dict[str, Any]:
    """List glossary terms, optionally scoped to one glossary FQN."""
    params: dict[str, Any] = {"limit": limit, "fields": "parent,synonyms,relatedTerms"}
    if glossary_fqn:
        params["glossary"] = glossary_fqn
    resp = get_client().get("/glossaryTerms", params=params)
    return {"count": len(resp.get("data", [])), "terms": resp.get("data", [])}


@tool
def get_glossary_term(fqn: str) -> dict[str, Any]:
    """Fetch a single glossary term by FQN."""
    return get_client().get_entity_by_fqn(
        "glossaryTerms", fqn, fields="children,parent,synonyms,relatedTerms,tags",
    )


@tool
def search_glossary_terms(query: str, limit: int = 20) -> dict[str, Any]:
    """Full-text search over glossary terms."""
    resp = get_client().search(query=query or "*", index="glossary_term_search_index", size=limit)
    hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
    return {"count": len(hits), "terms": hits}


@tool
def find_similar_terms(term_name: str, threshold: float = 0.75, limit: int = 200) -> dict[str, Any]:
    """Detect near-duplicate terms across all glossaries."""
    all_terms = get_client().get("/glossaryTerms", params={"limit": limit, "fields": "parent"}).get("data", [])
    matches = []
    lower_target = term_name.lower()
    for t in all_terms:
        name = t.get("name") or ""
        if name.lower() == lower_target:
            continue
        score = SequenceMatcher(None, lower_target, name.lower()).ratio()
        if score >= threshold:
            matches.append({
                "fqn": t.get("fullyQualifiedName"),
                "name": name,
                "glossary": (t.get("parent") or {}).get("fullyQualifiedName"),
                "similarity": round(score, 3),
            })
    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return {"query": term_name, "threshold": threshold, "matches": matches}


@tool
def link_asset_to_term(asset_fqn: str, term_fqn: str, entity_type: str = "tables", confirm: bool = False) -> dict[str, Any]:
    """Attach a glossary term as a tag on an asset. Requires confirm=True."""
    client = get_client()
    entity = client.get_entity_by_fqn(entity_type, asset_fqn, fields="tags")
    current = entity.get("tags") or []
    if any(t.get("tagFQN") == term_fqn for t in current):
        return {"applied": False, "reason": "Term already linked."}
    new_tags = current + [{"tagFQN": term_fqn, "source": "Glossary", "labelType": "Manual", "state": "Confirmed"}]
    patch = [{"op": "replace" if current else "add", "path": "/tags", "value": new_tags}]
    if not confirm:
        return {"applied": False, "dryRun": True, "patch": patch}
    client.patch(f"/{entity_type}/{entity['id']}", patch)
    return {"applied": True, "asset": asset_fqn, "term": term_fqn}


@tool
def list_assets_linked_to_term(term_fqn: str, limit: int = 50) -> dict[str, Any]:
    """List assets tagged with a given glossary term."""
    resp = get_client().search(query=f'tags.tagFQN:"{term_fqn}"', index="table_search_index", size=limit)
    hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
    return {"term": term_fqn, "count": len(hits), "assets": hits}
