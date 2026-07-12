# Tests

Pytest suite covering the OpenMetadata client wrapper and every tool module. HTTP calls are mocked with `respx`, so tests run offline and never hit AWS or a real OpenMetadata.

## Run

```bash
cd mcp_server
pip install -r requirements-dev.txt
pytest -v
```

## What's covered

| File | Focus |
| --- | --- |
| `test_openmetadata_client.py` | URL building, headers, JSON Patch content-type, error handling |
| `test_tools.py` | One representative test per tool module: discovery, documentation (dry-run + confirm), lineage, glossary similarity, golden-source scoring, quality rule suggestion, governance dashboard |

## Adding a new test

- Use the `tools` fixture to get a dict `{tool_name: callable}` — call tools directly like normal functions.
- Use the `mock_om` fixture (respx router mounted on the test host) to stub OpenMetadata endpoints.
- Sample payloads live in `conftest.py` — extend them there for reuse.
