---
name: document-asset
description: Guide a Data Owner through documenting one asset (table/dashboard/pipeline) end-to-end. Fetches the current schema, asks for business context, drafts a description, and proposes column-level descriptions before writing.
---

# Document Asset

Use this skill when a Data Owner wants to properly document a single asset in the catalog.

## When to trigger

- The user says "document this table", "describe this dataset", or references a specific FQN.
- The user asks to fill in missing descriptions on an asset they own.

## Procedure

1. **Confirm the target.** Ask for the fully-qualified name (FQN) if not given. Never guess.

2. **Fetch current state.** Call `get_asset_schema(fqn)` to retrieve columns and any existing descriptions. Show the user what's already there — do not overwrite silently.

3. **Gather business context.** Ask 3 targeted questions:
   - Which business process produces or consumes this asset?
   - What is the grain (one row = ?) and refresh frequency?
   - Any known caveats (deprecated columns, business rules, PII)?

4. **Draft the asset-level description.** Structure:
   - **Purpose** (one sentence: what business question does it answer)
   - **Grain** (one row = X)
   - **Refresh** (frequency + source system)
   - **Owner** (team / contact)
   - **Caveats** (if any)

5. **Draft per-column descriptions.** For every column without a description, propose one derived from the column name + data type + user context. Do not invent semantics you cannot justify — mark uncertain columns as `TBD by owner`.

6. **Dry-run first.** Call `propose_asset_description` and `propose_column_descriptions` — show the diff to the user.

7. **Apply on confirmation.** Only after explicit "yes / apply / confirm" from the user, call `apply_asset_description(confirm=True)` and `apply_column_descriptions(confirm=True)`.

## Anti-patterns to avoid

- Do not batch-apply across multiple assets in this skill — use `review-undocumented-backlog` for that.
- Do not write descriptions that just restate the column name (e.g. "customer_id: the customer ID").
- Do not tag PII or Tier without explicit confirmation — those are separate skills.
