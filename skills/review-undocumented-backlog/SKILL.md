---
name: review-undocumented-backlog
description: Walk a Data Owner through their backlog of undocumented assets. Prioritizes by usage and impact, then batches documentation reviews.
---

# Review Undocumented Backlog

Use this skill when a Data Owner asks "what do I have left to document?" or wants to catch up on documentation debt.

## Procedure

1. **Identify the perimeter.** Ask which owner (user or team name) or domain to scope. Default to the current user's team.

2. **Pull the backlog.** Call `list_undocumented_assets(owner_name=..., limit=100)`. Report the count first — this frames the effort.

3. **Prioritize.** For each asset (or a top-20 subset), enrich with usage signals via `get_asset(fqn)` and rank by `usageSummary.weeklyStats.count` descending. High-usage undocumented assets are the priority.

4. **Present the ranked list.** Table form: FQN, weekly queries, has_owner, downstream_count (call `find_impact_scope` for top 5 only — it's expensive).

5. **Ask the user to pick.** Do not batch-document without human input. For each chosen asset, delegate to the `document-asset` skill.

6. **Track progress.** At the end, summarize: N documented, M skipped, K deferred. If the user wants a recurring cadence, suggest scheduling `monthly-stewardship-report`.

## Anti-patterns

- Do not auto-generate descriptions for every backlog item — that produces low-quality metadata that erodes trust in the catalog.
- Do not skip the impact scan for high-usage assets — a bad description on a heavily-queried table propagates fast.
