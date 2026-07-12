from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx

from config import get_config


class OpenMetadataError(RuntimeError):
    pass


class OpenMetadataClient:
    """Sync httpx client with a persistent connection pool (warm across Lambda invocations)."""

    def __init__(self, host: str, jwt: str, timeout: float) -> None:
        self._client = httpx.Client(
            base_url=f"{host}/api/v1",
            headers={"Authorization": f"Bearer {jwt}", "Accept": "application/json"},
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10, keepalive_expiry=60.0),
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise OpenMetadataError(f"{method} {path} → {resp.status_code}: {resp.text[:400]}")
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params={k: v for k, v in (params or {}).items() if v is not None})

    def patch(self, path: str, patch_ops: list[dict[str, Any]]) -> Any:
        resp = self._client.patch(
            path,
            content=json.dumps(patch_ops).encode("utf-8"),
            headers={"Content-Type": "application/json-patch+json"},
        )
        if resp.status_code >= 400:
            raise OpenMetadataError(f"PATCH {path} → {resp.status_code}: {resp.text[:400]}")
        return resp.json()

    # -------------------------------------------------------------- helpers
    def search(self, query: str, index: str = "table_search_index", size: int = 20) -> dict[str, Any]:
        return self.get("/search/query", params={"q": query or "*", "index": index, "size": size})

    def get_entity_by_fqn(self, entity_type: str, fqn: str, fields: str | None = None) -> Any:
        return self.get(
            f"/{entity_type}/name/{quote(fqn, safe='')}",
            params={"fields": fields} if fields else None,
        )

    def get_entity_by_id(self, entity_type: str, entity_id: str, fields: str | None = None) -> Any:
        return self.get(
            f"/{entity_type}/{entity_id}",
            params={"fields": fields} if fields else None,
        )

    def get_lineage(self, entity_type: str, entity_id: str, upstream: int = 3, downstream: int = 3) -> Any:
        return self.get(
            f"/lineage/{entity_type}/{entity_id}",
            params={"upstreamDepth": upstream, "downstreamDepth": downstream},
        )


_CLIENT: OpenMetadataClient | None = None


def get_client() -> OpenMetadataClient:
    global _CLIENT
    if _CLIENT is None:
        cfg = get_config()
        _CLIENT = OpenMetadataClient(cfg.openmetadata_host, cfg.openmetadata_jwt, cfg.request_timeout)
    return _CLIENT
