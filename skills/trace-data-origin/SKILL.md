---
name: trace-data-origin
description: Explain in business language where a piece of data comes from. Walks upstream lineage, identifies source systems, and translates the chain into a narrative the business can understand.
---

# Trace Data Origin

Use this skill when someone asks "where does this data come from?", "what is the source of X?", or wants to verify provenance before a decision.

## Procedure

1. **Identify the target.** Ask for the FQN (or an asset name to disambiguate via `search_assets`).

2. **Walk upstream.** Call `trace_to_source(fqn, max_hops=10)`. Note the `rootSources` — these are the raw system entry points.

3. **Enrich the chain.** For each hop and each root source, call `get_asset(fqn)` to fetch:
   - Owner
   - Source system (from the FQN prefix: e.g. `prod_snowflake` vs `prod_kafka`)
   - Description (may already contain the business context)

4. **Look for column-level lineage.** If the user is asking about a specific column, call `get_column_lineage(fqn)` and follow the column's trace specifically.

5. **Translate.** Produce a narrative in the following shape:
   > "`sales_summary.total_orders_eur` comes from `raw_snowflake.sales_events` (owned by Team Commerce), which is loaded by the pipeline `kafka_to_snowflake_sales` from the Kafka topic `sales.events.v1`. That topic is produced by the checkout microservice."

6. **Flag concerns.** If any hop lacks an owner, description, or golden-source tier, mention it — provenance is only as trustworthy as its weakest link.

## Anti-patterns

- Do not present raw lineage graphs to a business user — always narrate.
- Do not conflate "table exists in the catalog" with "table is the source of truth". Check tier tags.
