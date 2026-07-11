---
name: certify-golden-source
description: Certify an asset as the golden source for a business concept. Enforces prerequisites (owner, description, tests, tier) before promotion and communicates the decision.
---

# Certify Golden Source

Use this skill after `arbitrate-golden-source` has produced a recommendation and the Data Owner is ready to promote the winning candidate.

## Procedure

1. **Confirm the candidate.** Restate: "you want to certify `<fqn>` as the golden source for `<concept>` — correct?"

2. **Verify prerequisites.** Call `assess_source_quality(fqn)`. The following must be true before certification:
   - `signals.hasOwner == true`
   - `signals.hasDescription == true`
   - `signals.hasTestSuite == true`
   - Column-level descriptions present on at least the primary key + measure columns (call `get_column_descriptions(fqn)`)

3. **Block on gaps.** If any prerequisite fails, do NOT certify. Instead, list the gaps and offer to chain to the relevant skill (`document-asset`, `propose-data-quality-rules`, `governance` tools for ownership).

4. **Certify.** Once prerequisites pass and the user explicitly confirms:
   - Dry-run `certify_asset(fqn, tier="Tier1")` to show the patch.
   - On second confirmation, call `certify_asset(fqn, tier="Tier1", confirm=True)`.

5. **Handle the runners-up.** For each competing asset from the arbitrage:
   - Do NOT auto-deprecate. Ask the user how they want to handle them: deprecate, downgrade to Tier 3, or leave as-is with a note.
   - If deprecating, chain to `impact-analysis` first — you need to know what breaks.

6. **Announce.** Draft a short communication for the domain's stakeholders:
   - What concept was arbitrated
   - Which asset is now the golden source
   - What the runners-up become
   - Where to find the certification (link to the OpenMetadata entity page)

## Anti-patterns

- Do not certify to fix a gap. Certification is recognition of quality, not aspiration.
- Do not skip the prerequisites check even if the user pushes. That's the whole point of the skill.
