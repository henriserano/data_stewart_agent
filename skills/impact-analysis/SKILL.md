---
name: impact-analysis
description: Assess the blast radius of a schema change, deprecation, or SLA breach on an asset. Lists downstream dependencies, identifies affected owners, and drafts stakeholder communications.
---

# Impact Analysis

Use this skill before making or announcing a change that could break downstream consumers: dropping a column, renaming a table, changing refresh frequency, deprecating a source.

## Procedure

1. **Frame the change.** Ask the user precisely: "which asset, what change, what timing?"

2. **Get the impact scope.** Call `find_impact_scope(fqn, depth=5)`. Note the `impactedCount` and the enriched top-50 with owners.

3. **Segment by owner.** Group impacted assets by owner team. This becomes the stakeholder map.

4. **Column-level check.** If the change is column-specific (rename, drop, type change), call `get_column_lineage(fqn)` and only keep the downstreams that reference that column.

5. **Score criticality.** For the top 10 downstreams, call `get_asset(fqn)` and check `tier` and `usageSummary`. Tier 1 or high-usage assets get a red flag.

6. **Draft the communication.** For each affected owner team, produce a short message:
   - What is changing
   - When
   - What their team needs to do
   - Contact for questions

7. **Do not send it automatically.** Present the drafts to the user for review. This skill only prepares — it does not communicate.

## Anti-patterns

- Do not assume the catalog captures 100% of lineage — external BI tools, reverse ETL, or handwritten SQL may not be tracked. State this caveat.
- Do not skip the tier check — a low-usage Tier 1 asset (e.g. regulatory report) can be more critical than a high-usage Tier 3.
