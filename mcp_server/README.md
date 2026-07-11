# Data Steward MCP Server

MCP server exposing OpenMetadata operations for an operational Data Steward assistant. Ships ~35 tools across 7 domains: discovery, documentation, lineage, glossary, golden source, quality, governance.

## Architecture

```
Claude Desktop / Claude for Work
        │  streamable HTTP + Bearer token
        ▼
AWS Lambda Function URL (RESPONSE_STREAM, ARM64, 512MB)
        │
        ▼
FastMCP (Python) → OpenMetadata REST API
        │
        └── SSM Parameter Store (SecureString) for the OpenMetadata JWT + bearer token
```

**Cost profile.** With free tier: **$0/mo** for typical POC traffic. Post-free-tier back-of-envelope for ~10k invocations/month at 500ms average: ~$0.08 Lambda + ~$0.05 CloudWatch Logs (3-day retention) + $0 SSM Standard + $0 Function URL. Well under $1/mo unless the agent is heavily used.

## Prerequisites

- AWS account, AWS CLI configured, SAM CLI installed
- Python 3.12
- OpenMetadata instance reachable from AWS Lambda (public URL or VPC + NAT/PrivateLink)
- OpenMetadata bot user with a JWT that has `ViewAll` + `EditAll` on the entities you plan to touch

## One-time setup: SSM parameters

```bash
aws ssm put-parameter \
  --name /data-steward/openmetadata-jwt \
  --value "eyJhbGciOi..." \
  --type SecureString

aws ssm put-parameter \
  --name /data-steward/mcp-bearer-token \
  --value "$(openssl rand -hex 32)" \
  --type SecureString
```

Note the bearer token value — you will paste it into Claude Desktop config.

## Deploy

```bash
cd mcp_server
cp samconfig.toml.example samconfig.toml   # then edit region + OpenMetadataHost
sam build
sam deploy --guided                        # first run only, then `sam deploy`
```

The stack output `FunctionUrl` is the endpoint you wire into Claude.

## Wire into Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "data-steward": {
      "url": "https://<hash>.lambda-url.eu-west-3.on.aws/mcp",
      "headers": {
        "Authorization": "Bearer <the-bearer-token-you-put-in-SSM>"
      }
    }
  }
}
```

Restart Claude Desktop. The `data-steward` tools appear in the tool picker.

## Wire into Claude for Work (org-wide)

In the Claude for Work admin console → Integrations → Add MCP Server → paste the Function URL + Bearer header. Publish to the workspace. All members inherit the connection.

## Local development

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in
uvicorn src.app:asgi_app --reload --port 8000
```

Then point a local MCP client at `http://localhost:8000/mcp` with the same bearer.

## Tool inventory

| Module | Tools |
| --- | --- |
| discovery | search_assets, get_asset, get_asset_schema, list_assets_by_owner, list_undocumented_assets, list_assets_by_domain, list_assets_by_tag |
| documentation | get_asset_description, get_column_descriptions, propose_asset_description, apply_asset_description, propose_column_descriptions, apply_column_descriptions |
| lineage | get_upstream_lineage, get_downstream_lineage, trace_to_source, find_impact_scope, get_column_lineage |
| glossary | list_glossaries, list_glossary_terms, get_glossary_term, search_glossary_terms, find_similar_terms, link_asset_to_term, list_assets_linked_to_term |
| golden_source | find_golden_source_candidates, list_certified_assets, compare_assets, assess_source_quality, certify_asset |
| quality | list_test_cases, get_test_case, get_test_results, list_assets_without_tests, suggest_test_cases, get_test_summary |
| governance | get_asset_owner, list_orphan_assets, propose_ownership, list_teams, list_domains, get_stewardship_dashboard |

**Write safety.** Every mutation tool (`apply_*`, `certify_*`, `propose_ownership`, `link_asset_to_term`) requires `confirm=True`. Without it, the server returns a dry-run patch for the user to review before applying.

## Security notes

- Bearer token is a shared secret — rotate via `aws ssm put-parameter --overwrite`.
- For production, move to IAM auth on the Function URL + a small proxy for header signing, or place behind API Gateway with a Cognito authorizer.
- The MCP server never reads business data — only metadata. It cannot exfiltrate rows from your warehouse.
