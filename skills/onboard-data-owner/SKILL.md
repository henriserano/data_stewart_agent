---
name: onboard-data-owner
description: Produce a first-week dashboard for a new Data Owner. Inventories their perimeter, ranks gaps by criticality, and outputs a 30-day plan.
---

# Onboard Data Owner

Use this skill when a new Data Owner joins and needs to understand what they inherit.

## Procedure

1. **Identify the owner.** Ask for their team name in the catalog (or the outgoing owner they're replacing).

2. **Pull the dashboard.** Call `get_stewardship_dashboard(owner_name)`. This gives asset count, undocumented count, no-tests count, no-tier count.

3. **Enrich with lineage weight.** For the top 10 most-used assets in the perimeter (use `list_assets_by_owner` then sort by `usageSummary`), run `find_impact_scope(fqn, depth=3)`. These are the assets whose degradation would hurt the most downstreams.

4. **Produce a first-week brief.** Structure:
   - **Your perimeter** — N assets, split by entity type
   - **Top 10 critical assets** — ranked by usage × downstream count, with current documentation state
   - **Documentation debt** — X assets undocumented, of which Y are Tier 1 or heavily used
   - **Quality debt** — X assets without any tests, list top offenders
   - **Ownership gaps** — assets in your perimeter with no downstream owner (they'll come back to you)

5. **Draft a 30-day plan.** Concrete deliverables week by week:
   - Week 1: read this brief, meet outgoing owner, confirm perimeter
   - Week 2: document top 5 critical assets (chain to `document-asset`)
   - Week 3: define QA rules for top 5 (chain to `propose-data-quality-rules`)
   - Week 4: review referential overlaps in your domain (chain to `align-referentials`)

## Anti-patterns

- Do not overwhelm with the full asset list. A 200-asset dump helps no one. Focus on the 10 that matter most.
- Do not assume the previous owner did everything wrong — flag debt but note what's already in place.
