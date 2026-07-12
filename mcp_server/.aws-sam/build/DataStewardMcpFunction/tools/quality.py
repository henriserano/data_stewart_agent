"""Data quality: a-priori tests and a-posteriori results."""
from __future__ import annotations

from typing import Any

from openmetadata_client import get_client
from tools._registry import tool

TYPE_TO_RULES = {
    "VARCHAR": ["columnValuesToNotBeNull", "columnValueLengthsToBeBetween"],
    "TEXT": ["columnValuesToNotBeNull", "columnValueLengthsToBeBetween"],
    "INT": ["columnValuesToNotBeNull", "columnValuesToBeBetween"],
    "BIGINT": ["columnValuesToNotBeNull", "columnValuesToBeBetween"],
    "DECIMAL": ["columnValuesToNotBeNull", "columnValuesToBeBetween"],
    "NUMERIC": ["columnValuesToNotBeNull", "columnValuesToBeBetween"],
    "TIMESTAMP": ["columnValuesToNotBeNull", "columnValuesToBeInRangeOfLast"],
    "DATE": ["columnValuesToNotBeNull", "columnValuesToBeInRangeOfLast"],
    "BOOLEAN": ["columnValuesToNotBeNull"],
}


@tool
def list_test_cases(asset_fqn: str | None = None, limit: int = 50) -> dict[str, Any]:
    """List data-quality test cases, optionally scoped to one asset."""
    params: dict[str, Any] = {"limit": limit, "fields": "testSuite,testDefinition"}
    if asset_fqn:
        params["entityLink"] = f"<#E::table::{asset_fqn}>"
    resp = get_client().get("/dataQuality/testCases", params=params)
    return {"count": len(resp.get("data", [])), "testCases": resp.get("data", [])}


@tool
def get_test_case(fqn: str) -> dict[str, Any]:
    """Get a single test case by FQN."""
    return get_client().get_entity_by_fqn(
        "dataQuality/testCases", fqn, fields="testSuite,testDefinition,testCaseResult",
    )


@tool
def get_test_results(test_case_fqn: str, limit: int = 10) -> dict[str, Any]:
    """Retrieve recent execution results for a test case."""
    resp = get_client().get(
        f"/dataQuality/testCases/name/{test_case_fqn}/testCaseResult", params={"limit": limit},
    )
    return {"testCase": test_case_fqn, "results": resp.get("data", [])}


@tool
def list_assets_without_tests(entity_type: str = "table", owner_name: str | None = None, limit: int = 50) -> dict[str, Any]:
    """List assets that have no test suite attached."""
    parts = ["NOT testSuite:*"]
    if owner_name:
        parts.append(f'owners.displayName:"{owner_name}"')
    resp = get_client().search(query=" AND ".join(parts), index=f"{entity_type}_search_index", size=limit)
    hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
    return {"count": len(hits), "assets": hits}


@tool
def suggest_test_cases(fqn: str) -> dict[str, Any]:
    """Propose data-quality rules based on schema type and column naming."""
    entity = get_client().get_entity_by_fqn("tables", fqn, fields="columns")
    suggestions = []
    for c in entity.get("columns", []):
        dtype = (c.get("dataType") or "").upper()
        for rule in TYPE_TO_RULES.get(dtype, ["columnValuesToNotBeNull"]):
            suggestions.append({"column": c.get("name"), "dataType": dtype, "testDefinition": rule})
        name_lower = (c.get("name") or "").lower()
        if name_lower.endswith("_id") or name_lower == "id":
            suggestions.append({"column": c.get("name"), "testDefinition": "columnValuesToBeUnique"})
    return {"fqn": fqn, "suggestionCount": len(suggestions), "suggestions": suggestions}


@tool
def get_test_summary(asset_fqn: str) -> dict[str, Any]:
    """A-posteriori snapshot: latest pass/fail counts on an asset's tests."""
    tests = get_client().get(
        "/dataQuality/testCases",
        params={"entityLink": f"<#E::table::{asset_fqn}>", "fields": "testCaseResult", "limit": 200},
    ).get("data", [])
    summary = {"success": 0, "failed": 0, "aborted": 0, "queued": 0, "total": len(tests)}
    details = []
    for t in tests:
        result = (t.get("testCaseResult") or {}).get("testCaseStatus")
        key = {"Success": "success", "Failed": "failed", "Aborted": "aborted"}.get(result, "queued")
        summary[key] += 1
        details.append({"name": t.get("name"), "status": result})
    return {"asset": asset_fqn, "summary": summary, "tests": details}
