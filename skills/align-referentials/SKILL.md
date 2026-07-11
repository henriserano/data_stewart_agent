---
name: align-referentials
description: Detect and reconcile overlaps between business glossaries. Finds near-duplicate terms across glossaries, proposes merges or hierarchies, and links unlinked assets.
---

# Align Referentials

Use this skill when a Data Owner suspects their glossaries have drifted (e.g. "Customer" defined differently in Sales and Finance glossaries) or wants to consolidate terminology across domains.

## Procedure

1. **Inventory.** Call `list_glossaries()` and `list_glossary_terms(limit=500)` to get the full referential landscape.

2. **Detect overlaps.** For each candidate term the user cares about (or a pass over top-20 by asset attachment count), call `find_similar_terms(term_name, threshold=0.75)`.

3. **Present clusters.** Group similar terms into clusters. For each cluster, show:
   - Which glossaries they live in
   - Whether definitions differ (fetch via `get_glossary_term`)
   - How many assets are linked to each (`list_assets_linked_to_term`)

4. **Recommend actions per cluster.**
   - **Merge:** if definitions are equivalent, pick a canonical term and mark others as synonyms.
   - **Distinguish:** if definitions genuinely differ (e.g. "Customer" in Sales = anyone who bought once vs "Customer" in Finance = anyone with an active contract), rename to disambiguate.
   - **Hierarchy:** if one is a specialization of the other, propose parent/child structure.

5. **Do not merge automatically.** Referential decisions are governance decisions. Present the recommendation, wait for user validation, then chain to specific link actions (`link_asset_to_term`).

## Anti-patterns

- Do not rely on name similarity alone. Two terms with identical names may have different meanings. Always compare descriptions.
- Do not delete terms with attached assets without impact analysis — the assets lose their business tagging.
