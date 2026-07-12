# Data Steward MCP Server

Lambda-native MCP server exposing OpenMetadata operations for a Data Steward assistant. 42 tools across 7 domains: discovery, documentation, lineage, glossary, golden source, quality, governance.

## Architecture

```
Claude Desktop / ChatGPT MCP
        │  HTTPS + Bearer token
        ▼
AWS Lambda Function URL (ARM64, 512 MB, BUFFERED)
        │  handler = plain Python, no ASGI framework
        ▼
httpx (persistent connection pool) → OpenMetadata REST API
        │
        └── SSM SecureString for the OpenMetadata JWT + MCP bearer token
```

No LWA layer, no uvicorn, no Starlette, no MCP SDK server. The handler speaks JSON-RPC 2.0 directly against Lambda Function URL events. Deployment package: **~2.3 MB**. Cold start: **~600 ms**. Warm invocations: **~60 ms** + OpenMetadata round-trip.

## Two deployment targets

| Target | OpenMetadataHost | Cost | When |
| --- | --- | --- | --- |
| **POC / demo** | `https://sandbox.open-metadata.org` (public OM sandbox) | $0 | Now, until you have a real catalog to point at |
| **Prod** | Your OpenMetadata on EC2 in the same region | ~$15/mo for a `t4g.small` | Client demos, real data, writes that persist |

The Lambda deployment is identical in both cases — only the `OpenMetadataHost` parameter changes.

## Prerequisites

- AWS account, AWS CLI configured, SAM CLI installed (`brew install aws-sam-cli`)
- Python 3.12
- An OpenMetadata JWT (bot user or personal access token) with `ViewAll` and, if you want writes, `EditAll`

## One-time setup — SSM parameters

```bash
aws ssm put-parameter --name /data-steward/openmetadata-jwt \
  --value "eyJhbGciOi..." --type SecureString --region eu-west-3

aws ssm put-parameter --name /data-steward/mcp-bearer-token \
  --value "$(openssl rand -hex 32)" --type SecureString --region eu-west-3
```

Note the bearer value — you paste it into your MCP client config.

## Deploy

```bash
cd mcp_server
cp samconfig.toml.example samconfig.toml   # edit region and OpenMetadataHost
sam build
sam deploy                                 # non-interactive after first run
```

The stack outputs `FunctionUrl` — that is the endpoint you wire into your MCP client.

## Wire into Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "data-steward": {
      "url": "https://<hash>.lambda-url.eu-west-3.on.aws/mcp",
      "headers": {
        "Authorization": "Bearer <your-bearer-from-SSM>"
      }
    }
  }
}
```

Fully quit Claude Desktop (`Cmd+Q` — closing the window is not enough) and relaunch. The 42 tools appear in the tool picker.

## Wire into ChatGPT (MCP support)

In ChatGPT settings, add a custom MCP server:
- URL: your Function URL + `/mcp`
- Header: `Authorization: Bearer <your-bearer-from-SSM>`

## Wire into Claude for Work (org-wide)

Admin console → Integrations → Add MCP Server → paste Function URL + Bearer header → Publish to workspace.

## Verify the deployment

```bash
FUNCTION_URL="https://<your-hash>.lambda-url.eu-west-3.on.aws"
BEARER=$(aws ssm get-parameter --name /data-steward/mcp-bearer-token \
  --with-decryption --region eu-west-3 --query 'Parameter.Value' --output text)

# Health probe — no auth
curl -sS "$FUNCTION_URL/health"

# MCP initialize
curl -sS -X POST "$FUNCTION_URL/mcp" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0.1"}}}'

# List tools
curl -sS -X POST "$FUNCTION_URL/mcp" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# Call a tool
curl -sS -X POST "$FUNCTION_URL/mcp" \
  -H "Authorization: Bearer $BEARER" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_teams","arguments":{"limit":5}}}'
```

## Iteration workflow

Fast redeploy for code changes (~15s vs ~2min):
```bash
sam sync --stack-name data-steward-mcp-poc --region eu-west-3 --watch
```

Force new containers to pick up updated SSM parameters:
```bash
aws lambda update-function-configuration --function-name data-steward-mcp \
  --region eu-west-3 --description "reload $(date +%s)"
```

Watch logs in real-time:
```bash
aws logs tail /aws/lambda/data-steward-mcp --region eu-west-3 --follow --format short
```

## Cost profile

- Lambda ARM64 + Function URL: covered by AWS free tier for POC volumes
- CloudWatch Logs at 3-day retention: cents/mo
- SSM Parameter Store Standard: free
- Egress for OpenMetadata API calls: negligible (metadata payloads are small)

**Total for POC: ~$0/month.**

Add EC2 for prod-hosted OpenMetadata: ~$15/mo (`t4g.small`) or ~$25/mo (`t4g.medium` — recommended, OM likes 4 GB RAM).

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

**Write safety.** Every mutation tool (`apply_*`, `certify_*`, `propose_ownership`, `link_asset_to_term`) requires `confirm=True`. Without it, the server returns a dry-run JSON Patch for review.

## Local development (optional)

If you want to iterate on tool code without redeploying to AWS, run the server as a plain HTTP app locally:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env    # fill in OPENMETADATA_HOST / JWT / bearer

set -a && source .env && set +a
pip install uvicorn starlette
python -m uvicorn app_local:asgi_app --app-dir src --port 8080 --reload
```

Note: local dev requires an `app_local.py` shim that wraps the JSON-RPC handler in a Starlette route. Not shipped by default because the deployment path is Lambda-first. For prod dev iteration, prefer `sam sync --watch`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

19 tests covering the OpenMetadata client + representative tool behavior (dry-run/confirm gates, scoring, schema-driven suggestions, lineage traversal). All mocks via `respx`, no live network required.

## Security notes

- Bearer token is a shared secret. Rotate via `aws ssm put-parameter --overwrite` then force container recycling.
- The MCP server reads and writes **metadata only** — it cannot query business rows from your warehouse.
- For prod, put the Function URL behind IAM auth or API Gateway + Cognito if bearer isn't enough.
