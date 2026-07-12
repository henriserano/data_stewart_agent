# Data Steward Agent — Sia

Operational assistant for a Data Owner. Ships as a **Lambda-native MCP server** (42 tools on top of OpenMetadata) + **11 Claude Skills** that package the operational workflows. Metadata only, never touches business data.

Scope of the assistant, aligned with the L'Oréal PO Data role reference:
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
├── mcp_server/                  # MCP server (Python 3.12, AWS SAM)
│   ├── README.md                # deployment + verification guide
│   ├── template.yaml            # AWS SAM template (Lambda ARM64 + Function URL)
│   ├── samconfig.toml.example
│   ├── pyproject.toml, requirements.txt, requirements-dev.txt
│   ├── src/
│   │   ├── app.py               # Lambda handler + JSON-RPC dispatcher
│   │   ├── config.py            # env vars + SSM batch fetch
│   │   ├── openmetadata_client.py
│   │   └── tools/               # 7 modules registering 42 @tool functions
│   └── tests/                   # pytest suite (respx mocks)
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
┌───────────────────────────────────────┐
│ Data Owner in Claude Desktop /        │
│ Claude for Work / ChatGPT             │
└──────────────┬────────────────────────┘
               │  (1) picks a Skill  (2) chats
               ▼
┌───────────────────────────────────────┐
│ Skill (SKILL.md)                      │
│  procedure + anti-patterns +          │
│  which MCP tools to call, in order    │
└──────────────┬────────────────────────┘
               │  (3) MCP JSON-RPC over HTTPS + Bearer
               ▼
┌───────────────────────────────────────┐
│ AWS Lambda (ARM64, 512 MB)            │
│ 42 tools across 7 modules             │
└──────────────┬────────────────────────┘
               │  (4) REST + JSON Patch
               ▼
┌───────────────────────────────────────┐
│ OpenMetadata                          │
│   POC : sandbox.open-metadata.org     │
│   Prod: self-hosted on EC2            │
└───────────────────────────────────────┘
```

## Deployment targets

| Target | OpenMetadata backend | Setup time | Monthly cost |
| --- | --- | --- | --- |
| POC / demo | Public OM sandbox (`sandbox.open-metadata.org`) | 10 min | **$0** |
| Prod | Self-hosted OM on an EC2 `t4g.medium` in eu-west-3 | ~1h first time | ~$25 |

The Lambda + skills package is identical between both. Only the `OpenMetadataHost` parameter changes on deploy.

## Getting started

1. **Deploy the MCP server on AWS.** Follow `mcp_server/README.md`. One `sam deploy` yields a Function URL.
2. **Wire your MCP client.**
   - Claude Desktop: paste Function URL + bearer into `claude_desktop_config.json` and fully quit + relaunch.
   - Claude for Work: publish org-wide via the admin console.
   - ChatGPT: add as a custom MCP server in settings.
3. **Load the skills.**
   - Local Claude Code: drop `skills/` into your project — auto-discovered.
   - Claude for Work: publish each SKILL.md via the admin console.

## Performance (measured against OpenMetadata sandbox)

| Path | Latency |
| --- | --- |
| Lambda cold start (`/health`) | ~600 ms |
| Lambda warm (`/health`) | ~60 ms |
| MCP `tools/list` warm | ~60 ms |
| MCP `tools/call` warm | ~170–210 ms (network to sandbox is the floor) |

Package size: **2.3 MB** deployed. Runtime: Python 3.12 ARM64. No LWA layer, no uvicorn, no ASGI framework — just a plain Lambda handler over the Function URL protocol.

## Positioning vs the two sister agents

This repo is the **Data Steward Agent**. Related work in the same parent folder:
- **Data Quality Agent** (`../Data Quality agent/`) — grounded QA-rule generation from data profiling.
- **Audit Agent** (referenced in `../Agent_idea.md`) — catalog snapshot + slide deliverable for a Sia audit.

The three overlap on the "propose-data-quality-rules" surface; here we scope QA to a-priori + a-posteriori signals only, and defer deeper profiling to the Data Quality Agent.

## Next steps

- Interview PO Data at L'Oréal to validate scope and confirm their platform.
- Extract the L'Oréal PO Data job description and map each responsibility to a specific tool or skill above.
- For prod demo: provision the EC2 running OpenMetadata in eu-west-3 and switch `OpenMetadataHost` at redeploy.
