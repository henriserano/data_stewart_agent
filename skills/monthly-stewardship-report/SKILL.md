---
name: monthly-stewardship-report
description: Generate a periodic health-check on a Data Owner's perimeter. Compares against last month if available, highlights new debt and closed items, produces an executive-ready summary.
---

# Monthly Stewardship Report

Use this skill on a monthly cadence, or when the Data Owner needs a snapshot for their manager or governance committee.

## Procedure

1. **Scope.** Confirm the owner team name and the reporting period (default: past 30 days).

2. **Snapshot current state.** Call `get_stewardship_dashboard(owner_name)`.

3. **Test health.** For the top 20 assets, call `get_test_summary(asset_fqn)` and aggregate: pass rate, failed tests, aborted tests.

4. **Recent changes.** If the tool set were extended with a `list_recent_changes` (not shipped by default), use it. Otherwise, note "recent-changes tracking not enabled — request that OpenMetadata activity feed be indexed for future reports."

5. **Produce the report.** Structure (Sia executive style, no em-dashes):
   - **Executive summary** — one paragraph. State the answer first: overall health rating (Green/Amber/Red), the single biggest risk, the single biggest win.
   - **Coverage** — assets, documented %, tier-1 %, tested %
   - **Quality** — pass rate on tests, top 5 failing tests
   - **Debt** — undocumented assets, orphan assets, referential overlaps (chain to `align-referentials` if flagging any)
   - **Next 30 days** — 3–5 specific commitments

6. **Format for deliverable.** Ready to paste into an email or slide. Follow Sia deliverable standards: lead with the answer, no hedging in the summary.

## Anti-patterns

- Do not present scores without context. A 40% documentation rate is bad in one domain and normal in another.
- Do not commit the Data Owner to next-month actions without their sign-off.
