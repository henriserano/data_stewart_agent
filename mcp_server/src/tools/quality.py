"""Data quality: a priori (defined tests) and a posteriori (test results) metadata."""
from __future__ import annotations

from typing import Any

from ..openmetadata_client import get_client


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


def register(mcp) -> None:
    @mcp.tool()
    def list_test_cases(asset_fqn: str | None = None, limit: int = 50) -> dict[str, Any]:
        """List data-quality test cases, optionally scoped to one asset."""
        params: dict[str, Any] = {"limit": limit, "fields": "testSuite,testDefinition"}
        if asset_fqn:
            params["entityLink"] = f"<#E::table::{asset_fqn}>"
        resp = get_client().get("/dataQuality/testCases", params=params)
        return {"count": len(resp.get("data", [])), "testCases": resp.get("data", [])}

    @mcp.tool()
    def get_test_case(fqn: str) -> dict[str, Any]:
        """Get a single test case by FQN."""
        return get_client().get_entity_by_fqn(
            "dataQuality/testCases",
            fqn,
            fields="testSuite,testDefinition,testCaseResult",
        )

    @mcp.tool()
    def get_test_results(test_case_fqn: str, limit: int = 10) -> dict[str, Any]:
        """Retrieve recent execution results for a test case."""
        resp = get_client().get(
            f"/dataQuality/testCases/name/{test_case_fqn}/testCaseResult",
            params={"limit": limit},
        )
        return {"testCase": test_case_fqn, "results": resp.get("data", [])}

    @mcp.tool()
    def list_assets_without_tests(entity_type: str = "table", owner_name: str | None = None, limit: int = 50) -> dict[str, Any]:
        """List assets that have no test suite attached (a-priori control gap)."""
        parts = ["NOT testSuite:*"]
        if owner_name:
            parts.append(f'owners.displayName:"{owner_name}"')
        resp = get_client().search(query=" AND ".join(parts), index=f"{entity_type}_search_index", size=limit)
        hits = [h["_source"] for h in resp.get("hits", {}).get("hits", [])]
        return {"count": len(hits), "assets": hits}

    @mcp.tool()
    def suggest_test_cases(fqn: str) -> dict[str, Any]:
        """From an asset's schema, propose data-quality rules to define (a-priori controls).

        Rules are drawn from OpenMetadata's built-in TestDefinitions. Nothing is written.
        """
        entity = get_client().get_entity_by_fqn("tables", fqn, fields="columns")
        suggestions: list[dict[str, Any]] = []
        for c in entity.get("columns", []):
            dtype = (c.get("dataType") or "").upper()
            base = TYPE_TO_RULES.get(dtype, ["columnValuesToNotBeNull"])
            for rule in base:
                suggestions.append({"column": c.get("name"), "dataType": dtype, "testDefinition": rule})
            # Always propose a uniqueness check on columns that look like keys.
            name = (c.get("name") or "").lower()
            if name.endswith("_id") or name == "id":
                suggestions.append({"column": c.get("name"), "testDefinition": "columnValuesToBeUnique"})
        return {"fqn": fqn, "suggestionCount": len(suggestions), "suggestions": suggestions}

    @mcp.tool()
    def get_test_summary(asset_fqn: str) -> dict[str, Any]:
        """A-posteriori snapshot: latest pass/fail counts for all test cases on an asset."""
        tests = get_client().get(
            "/dataQuality/testCases",
            params={"entityLink": f"<#E::table::{asset_fqn}>", "fields": "testCaseResult", "limit": 200},
        ).get("data", [])
        summary = {"success": 0, "failed": 0, "aborted": 0, "queued": 0, "total": len(tests)}
        details: list[dict[str, Any]] = []
        for t in tests:
            result = (t.get("testCaseResult") or {}).get("testCaseStatus")
            if result == "Success":
                summary["success"] += 1
            elif result == "Failed":
                summary["failed"] += 1
            elif result == "Aborted":
                summary["aborted"] += 1
            else:
                summary["queued"] += 1
            details.append({"name": t.get("name"), "status": result})
        return {"asset": asset_fqn, "summary": summary, "tests": details}
