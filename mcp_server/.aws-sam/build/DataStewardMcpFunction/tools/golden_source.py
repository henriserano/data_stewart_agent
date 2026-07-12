"""Golden source: rank candidates from a single search response (no N+1 enrichment)."""
from __future__ import annotations

from typing import Any

from openmetadata_client import get_client
from tools._registry import tool


def _score(entity: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    score = 0
    signals: dict[str, Any] = {}

    owners = entity.get("owners") or []
    signals["hasOwner"] = bool(owners)
    if owners:
        score += 20

    signals["hasDescription"] = bool(entity.get("description"))
    if entity.get("description"):
        score += 15

    tier = (entity.get("tier") or {}).get("tagFQN", "") if isinstance(entity.get("tier"), dict) else ""
    signals["tier"] = tier
    if "Tier1" in tier:
        score += 20
    elif "Tier2" in tier:
        score += 12
    elif "Tier3" in tier:
        score += 5

    weekly = (((entity.get("usageSummary") or {}).get("weeklyStats") or {}).get("count")) or 0
    signals["weeklyQueries"] = weekly
    if weekly > 100:
        score += 15
    elif weekly > 10:
        score += 8

    signals["hasTestSuite"] = entity.get("testSuite") is not None
    if entity.get("testSuite"):
        score += 15

    signals["hasProfile"] = (entity.get("profile") or {}).get("timestamp") is not None
    if signals["hasProfile"]:
        score += 15

    return min(score, 100), signals


@tool
def find_golden_source_candidates(business_concept: str, entity_type: str = "table", limit: int = 15) -> dict[str, Any]:
    """Search + rank candidates from ONE search response. No follow-up gets."""
    resp = get_client().search(query=business_concept, index=f"{entity_type}_search_index", size=limit)
    hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
    candidates = []
    for h in hits:
        score, signals = _score(h)
        candidates.append({
            "fqn": h.get("fullyQualifiedName"),
            "name": h.get("name"),
            "score": score,
            "signals": signals,
            "owners": [o.get("displayName") for o in h.get("owners") or []],
        })
    candidates.sort(key=lambda c: c.get("score", 0), reverse=True)
    return {"concept": business_concept, "candidates": candidates}


@tool
def list_certified_assets(tier: str = "Tier1", entity_type: str = "table", limit: int = 50) -> dict[str, Any]:
    """List assets certified at a given tier (Tier1 = golden source)."""
    resp = get_client().search(
        query=f'tier.tagFQN:"Tier.{tier}"', index=f"{entity_type}_search_index", size=limit,
    )
    hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
    return {"tier": tier, "count": len(hits), "assets": hits}


@tool
def compare_assets(fqn_a: str, fqn_b: str, entity_type: str = "tables") -> dict[str, Any]:
    """Side-by-side comparison of two assets on golden-source dimensions."""
    client = get_client()
    fields = "owners,tags,columns,description,tier,usageSummary,profile,testSuite"
    a = client.get_entity_by_fqn(entity_type, fqn_a, fields=fields)
    b = client.get_entity_by_fqn(entity_type, fqn_b, fields=fields)

    def _summary(e: dict[str, Any]) -> dict[str, Any]:
        score, signals = _score(e)
        return {
            "fqn": e.get("fullyQualifiedName"),
            "owners": [o.get("displayName") for o in e.get("owners") or []],
            "columnCount": len(e.get("columns") or []),
            "hasDescription": bool(e.get("description")),
            "tier": (e.get("tier") or {}).get("tagFQN") if isinstance(e.get("tier"), dict) else None,
            "score": score,
            "signals": signals,
        }

    sa, sb = _summary(a), _summary(b)
    return {"a": sa, "b": sb, "recommendation": "a" if sa["score"] >= sb["score"] else "b"}


@tool
def assess_source_quality(fqn: str, entity_type: str = "tables") -> dict[str, Any]:
    """Score a single asset's fitness as a golden source (0-100)."""
    entity = get_client().get_entity_by_fqn(
        entity_type, fqn, fields="owners,tier,usageSummary,profile,testSuite,description,tags",
    )
    score, signals = _score(entity)
    return {"fqn": fqn, "score": score, "signals": signals}


@tool
def certify_asset(fqn: str, tier: str = "Tier1", confirm: bool = False, entity_type: str = "tables") -> dict[str, Any]:
    """Promote an asset by attaching a Tier tag. Requires confirm=True."""
    client = get_client()
    entity = client.get_entity_by_fqn(entity_type, fqn, fields="tags")
    current = entity.get("tags") or []
    new_tags = [t for t in current if not (t.get("tagFQN") or "").startswith("Tier.")]
    new_tags.append({"tagFQN": f"Tier.{tier}", "source": "Classification", "labelType": "Manual", "state": "Confirmed"})
    patch = [{"op": "replace" if current else "add", "path": "/tags", "value": new_tags}]
    if not confirm:
        return {"applied": False, "dryRun": True, "patch": patch}
    client.patch(f"/{entity_type}/{entity['id']}", patch)
    return {"applied": True, "fqn": fqn, "tier": tier}
