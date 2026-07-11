---
name: arbitrate-golden-source
description: When multiple assets represent the same business concept, help the Data Owner pick the golden source. Scores candidates on ownership, documentation, quality, freshness, usage, then argues the recommendation.
---

# Arbitrate Golden Source

Use this skill when there are competing sources for the same concept (e.g. three "customer" tables across three domains) and the org needs one to be the reference.

## Procedure

1. **Name the business concept.** Ask the user: "which concept? (e.g. customer master, product SKU, sales order header)"

2. **Find candidates.** Call `find_golden_source_candidates(business_concept, entity_type="table", limit=15)`. The result is a pre-scored list.

3. **Deep-dive top 3–5.** For each of the top candidates, call `assess_source_quality(fqn)` to get the full signal breakdown.

4. **Compare pairwise.** For the top 2, call `compare_assets(fqn_a, fqn_b)`. Explain differences: ownership, column count, tier, freshness, test coverage.

5. **Recommend.** Argue for one candidate. Structure:
   - **Recommendation:** `<fqn>` — score `<n>/100`
   - **Strengths:** ownership, tests, tier, usage
   - **Gaps to close before certification:** documentation, missing tests, unowned columns
   - **Runners-up:** why they lose (typically: no owner, no tests, lower usage)

6. **Propose certification path.** If the user agrees, chain to the `certify-golden-source` skill.

## Anti-patterns

- Do not certify on score alone. Golden source is a governance decision that requires the Data Owner's business judgment. The score is decision support, not the decision.
- Do not deprecate the runners-up in the same conversation — that is a separate impact analysis (`impact-analysis`).
