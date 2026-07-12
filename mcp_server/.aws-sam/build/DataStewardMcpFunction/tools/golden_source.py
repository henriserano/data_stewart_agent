"""Golden source identification and certification."""
from __future__ import annotations

from typing import Any

from openmetadata_client import get_client


def _score_asset(entity: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """Heuristic score for source quality (0-100).

    Weights: ownership 20, description 15, tests 15, tier 20, freshness 15, usage 15.
    """
    score = 0
    signals: dict[str, Any] = {}

    owners = entity.get("owners") or []
    signals["hasOwner"] = bool(owners)
    if owners:
        score += 20

    signals["hasDescription"] = bool(entity.get("description"))
    if entity.get("description"):
        score += 15

    tier = (entity.get("tier") or {}).get("tagFQN", "")
    signals["tier"] = tier
    if "Tier1" in tier:
        score += 20
    elif "Tier2" in tier:
        score += 12
    elif "Tier3" in tier:
        score += 5

    usage = entity.get("usageSummary") or {}
    weekly = ((usage.get("weeklyStats") or {}).get("count")) or 0
    signals["weeklyQueries"] = weekly
    if weekly > 100:
        score += 15
    elif weekly > 10:
        score += 8

    profile = entity.get("profile") or {}
    signals["profileTimestamp"] = profile.get("timestamp")
    if profile.get("timestamp"):
        score += 10

    tests_pass = entity.get("testSuite") is not None
    signals["hasTestSuite"] = tests_pass
    if tests_pass:
        score += 15

    return min(score, 100), signals


def register(mcp) -> None:
    @mcp.tool()
    def find_golden_source_candidates(business_concept: str, entity_type: str = "table", limit: int = 15) -> dict[str, Any]:
        """Search catalog for assets matching a business concept, ranked by source-quality heuristic.

        Args:
            business_concept: e.g. "customer", "product master", "sales orders".
            entity_type: table, container, topic.
            limit: candidates to inspect (ranking pass is expensive on large lists).
        """
        client = get_client()
        resp = client.search(query=business_concept, index=f"{entity_type}_search_index", size=limit)
        hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
        candidates: list[dict[str, Any]] = []
        for h in hits:
            fqn = h.get("fullyQualifiedName")
            if not fqn:
                continue
            try:
                full = client.get_entity_by_fqn(
                    f"{entity_type}s",
                    fqn,
                    fields="owners,tier,usageSummary,profile,testSuite,description",
                )
                score, signals = _score_asset(full)
                candidates.append({
                    "fqn": fqn,
                    "name": full.get("name"),
                    "score": score,
                    "signals": signals,
                    "owners": [o.get("displayName") for o in full.get("owners") or []],
                })
            except Exception as e:
                candidates.append({"fqn": fqn, "error": str(e)[:200]})
        candidates.sort(key=lambda c: c.get("score", 0), reverse=True)
        return {"concept": business_concept, "candidates": candidates}

    @mcp.tool()
    def list_certified_assets(tier: str = "Tier1", entity_type: str = "table", limit: int = 50) -> dict[str, Any]:
        """List assets already certified at a given tier (Tier1 = golden source convention)."""
        resp = get_client().search(
            query=f'tier.tagFQN:"Tier.{tier}"',
            index=f"{entity_type}_search_index",
            size=limit,
        )
        hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
        return {"tier": tier, "count": len(hits), "assets": hits}

    @mcp.tool()
    def compare_assets(fqn_a: str, fqn_b: str, entity_type: str = "tables") -> dict[str, Any]:
        """Side-by-side comparison of two assets on the dimensions that matter for arbitrage."""
        client = get_client()
        a = client.get_entity_by_fqn(entity_type, fqn_a, fields="owners,tags,columns,description,tier,usageSummary,profile,testSuite")
        b = client.get_entity_by_fqn(entity_type, fqn_b, fields="owners,tags,columns,description,tier,usageSummary,profile,testSuite")

        def _summary(e: dict[str, Any]) -> dict[str, Any]:
            score, signals = _score_asset(e)
            return {
                "fqn": e.get("fullyQualifiedName"),
                "owners": [o.get("displayName") for o in e.get("owners") or []],
                "columnCount": len(e.get("columns") or []),
                "hasDescription": bool(e.get("description")),
                "tier": (e.get("tier") or {}).get("tagFQN"),
                "score": score,
                "signals": signals,
            }

        return {"a": _summary(a), "b": _summary(b), "recommendation": "a" if _score_asset(a)[0] >= _score_asset(b)[0] else "b"}

    @mcp.tool()
    def assess_source_quality(fqn: str, entity_type: str = "tables") -> dict[str, Any]:
        """Score a single asset's fitness as a golden source (0-100) with detailed signals."""
        client = get_client()
        entity = client.get_entity_by_fqn(
            entity_type,
            fqn,
            fields="owners,tier,usageSummary,profile,testSuite,description,tags",
        )
        score, signals = _score_asset(entity)
        return {"fqn": fqn, "score": score, "signals": signals}

    @mcp.tool()
    def certify_asset(fqn: str, tier: str = "Tier1", confirm: bool = False, entity_type: str = "tables") -> dict[str, Any]:
        """Promote an asset by attaching a Tier tag (e.g. Tier1 for golden source). Requires confirm=True."""
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
