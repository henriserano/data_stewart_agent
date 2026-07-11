# Data Steward Agent — Sia

Operational assistant for a Data Owner. Ships as **MCP server on AWS Lambda** + **11 Claude Skills**. Metadata only, never touches business data.

Scope of the assistant (aligned with the L'Oréal PO Data role reference):
- **Describe data** — asset and column-level documentation
- **A-priori controls** — define data-quality rules grounded in the schema
- **A-posteriori observations** — surface test results and health signals
- **Referential alignment** — reconcile glossary overlaps across domains
- **Golden source arbitrage** — pick, certify, promote reference assets
- **Data lineage** — trace where a data point comes from, in business language

## Repository layout

```
Data stewart Agent/
├── README.md                    # this file
├── mcp_server/                  # MCP server (Python, FastMCP, AWS SAM)
│   ├── README.md                # deployment guide
│   ├── template.yaml            # AWS SAM template
│   ├── src/
│   │   ├── app.py               # Lambda handler + FastMCP init
│   │   ├── config.py, auth.py, openmetadata_client.py
│   │   └── tools/               # 7 modules, ~35 tools
│   ├── pyproject.toml, requirements.txt
│   └── .env.example, samconfig.toml.example
└── skills/                      # 11 SKILL.md workflow definitions
    ├── README.md
    ├── document-asset/
    ├── review-undocumented-backlog/
    ├── trace-data-origin/
    ├── impact-analysis/
    ├── arbitrate-golden-source/
    ├── align-referentials/
    ├── onboard-data-owner/
    ├── monthly-stewardship-report/
    ├── propose-data-quality-rules/
    ├── link-assets-to-glossary/
    └── certify-golden-source/
```

## How the pieces fit

```
┌─────────────────────────────────────┐
│ Data Owner in Claude Desktop /      │
│ Claude for Work                     │
└──────────────┬──────────────────────┘
               │
               │  (1) selects a Skill (e.g. "document this table")
               │  (2) chats naturally
               │
               ▼
┌─────────────────────────────────────┐
│ Skill (SKILL.md)                    │
│ - procedure                         │
│ - anti-patterns                     │
│ - which MCP tools to call and when  │
└──────────────┬──────────────────────┘
               │  (3) Claude calls MCP tools
               ▼
┌─────────────────────────────────────┐
│ MCP server (AWS Lambda, ARM64)      │
│ - 35 tools: search, describe,       │
│   lineage, quality, glossary, ...   │
└──────────────┬──────────────────────┘
               │  (4) REST calls
               ▼
┌─────────────────────────────────────┐
│ OpenMetadata (or DataHub)           │
│ - metadata only, no business rows   │
└─────────────────────────────────────┘
```

## Getting started

1. **Deploy the MCP server.** Follow `mcp_server/README.md`. One `sam deploy` gets you a Function URL.
2. **Wire Claude Desktop** to that URL with a bearer token (config example in the same README).
3. **Load the skills.** Two options:
   - Local Claude Code: drop `skills/` into your project so Claude auto-discovers them.
   - Claude for Work: publish the skills you want via the admin console. Each skill folder is a self-contained artifact.

## Cost profile

- Lambda ARM64 + Function URL: covered by AWS free tier for POC volumes.
- CloudWatch Logs with 3-day retention: pennies.
- SSM Parameter Store Standard tier: free.
- No API Gateway, no NAT Gateway (unless your OpenMetadata is in a VPC — then reuse existing NAT).
- **Estimated monthly cost for POC usage: ~$0.**

## Positioning vs the two sister agents

This repo is the **Data Steward Agent**. Related work in the same parent folder:

- **Data Quality agent** (`../Data Quality agent/`) — grounded QA-rule generation, deeper focus on rule definition from data.
- **Audit agent** (referenced in `../Agent_idea.md`) — catalog snapshot + slides for a Sia audit deliverable.

The three overlap on the "propose-data-quality-rules" surface; here we scope QA to a-priori + a-posteriori signals only, and defer heavier profiling to the Data Quality agent.

## Next steps

- Interview PO Data at L'Oréal to validate scope, confirm platform (OpenMetadata assumed here), identify the top 3 workflows to demo.
- Extract the L'Oréal PO Data job description and map each responsibility to a specific tool or skill above.
- Decide whether to add write-heavy workflows (e.g. batch certification) or keep the assistant advisory-only in V1.
# data_stewart_agent
