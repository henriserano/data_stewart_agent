---
name: propose-data-quality-rules
description: From an asset's schema and business context, propose a-priori data-quality rules (test cases) grounded in the data itself, not in generic templates.
---

# Propose Data Quality Rules

Use this skill when a Data Owner wants to define quality controls for an asset and needs a starting point.

## Procedure

1. **Target the asset.** Ask for the FQN. Fetch schema via `get_asset_schema(fqn)`.

2. **Baseline suggestions.** Call `suggest_test_cases(fqn)`. This returns rules driven by column types and naming conventions (e.g. `columnValuesToNotBeNull`, `columnValuesToBeUnique` on `*_id` columns).

3. **Deepen with business rules.** Ask the user 3 targeted questions:
   - Are there columns with a known set of valid values (enums)? → propose `columnValuesToBeInSet`.
   - Are there numeric columns with known bounds (e.g. quantity > 0, price < 1e6)? → propose `columnValuesToBeBetween`.
   - Are there columns that must match a pattern (e.g. email, IBAN, product code)? → propose `columnValuesToMatchRegex`.

4. **Cross-column rules.** Ask if there are known relationships between columns (e.g. `end_date >= start_date`, `total = quantity * unit_price`). Propose `tableCustomSQLQuery` for those.

5. **Freshness.** Confirm the expected refresh cadence and propose `tableColumnCountToBeBetween` or `tableFreshnessCheck` (if configured).

6. **Present the ruleset.** Group by column, mark which are baseline (auto) vs business (user-informed). Estimate runtime cost (rough: 1s per rule for small tables, 10s+ for wide tables).

7. **Do not create test cases automatically.** OpenMetadata test creation is a governed action. Output the ruleset as YAML/JSON the user can paste into the OpenMetadata UI or a workflow file. If direct creation is required, it must be a separate skill with explicit confirmation.

## Anti-patterns

- Do not propose rules that cannot be justified by the data or the user's answers. "Nice to have" rules dilute the value of the ones that matter.
- Do not propose duplicate rules (a `NotNull` and a `Unique` cover different failures — both are fine; two `NotNull` on the same column are not).
