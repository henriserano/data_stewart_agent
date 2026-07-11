---
name: link-assets-to-glossary
description: Match technical assets (tables, columns) to business glossary terms. Suggests links based on names and descriptions, then applies on confirmation.
---

# Link Assets to Glossary

Use this skill when a Data Owner wants to enrich assets with business semantics — making them findable by business users searching for concepts, not table names.

## Procedure

1. **Scope.** Ask which subset: a single asset, a domain, or an owner's perimeter.

2. **Pull candidates.** For each asset in scope:
   - Fetch schema via `get_asset_schema(fqn)`.
   - For each column name that looks like a business concept (e.g. `customer_id`, `order_amount`), call `search_glossary_terms(query=column_name, limit=5)`.

3. **Score matches.** For each column ↔ term pair, judge:
   - Exact name match → high confidence
   - Synonym match (via `get_glossary_term.synonyms`) → medium
   - Semantic guess from description → low, flag for human review

4. **Present the mapping.** Table: asset, column, proposed term, confidence, existing link (yes/no).

5. **Apply in bulk with confirmation.** For high-confidence matches only, offer to call `link_asset_to_term(confirm=True)` in sequence. Medium/low go to a "review needed" list.

6. **Handle the gaps.** If a business concept appears in many assets but has no glossary term, flag it: "consider creating a term for `<concept>` in the `<domain>` glossary". Do not create terms automatically — that's a glossary owner decision.

## Anti-patterns

- Do not link low-confidence matches without explicit human validation. Bad tags pollute the catalog search worse than missing tags.
- Do not link asset-level terms and column-level terms interchangeably. A term on the whole table means "this asset is about concept X"; a term on a column means "this column represents concept X".
