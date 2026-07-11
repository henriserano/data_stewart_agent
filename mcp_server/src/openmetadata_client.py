from __future__ import annotations

from functools import lru_cache
from typing import Any
from urllib.parse import quote

import httpx

from .config import get_config


class OpenMetadataError(RuntimeError):
    """Raised when the OpenMetadata API returns an unsuccessful response."""


class OpenMetadataClient:
    """
    Thin wrapper around the OpenMetadata REST API.

    Docs: https://docs.open-metadata.org/swagger.html
    Also compatible with DataHub via its OpenMetadata-shaped REST layer when needed
    (a separate client would be cleaner if you dual-target both).
    """

    def __init__(self, host: str, jwt: str, timeout: float) -> None:
        self._client = httpx.Client(
            base_url=f"{host}/api/v1",
            headers={
                "Authorization": f"Bearer {jwt}",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    # ------------------------------------------------------------------ core
    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            raise OpenMetadataError(f"{method} {path} → {resp.status_code}: {resp.text[:500]}")
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=_clean(params))

    def post(self, path: str, json_body: Any = None) -> Any:
        return self._request("POST", path, json=json_body)

    def patch(self, path: str, patch_ops: list[dict[str, Any]]) -> Any:
        # OpenMetadata uses JSON Patch (RFC 6902) for entity updates.
        resp = self._client.patch(
            path,
            content=httpx_json_dumps(patch_ops),
            headers={"Content-Type": "application/json-patch+json"},
        )
        if resp.status_code >= 400:
            raise OpenMetadataError(f"PATCH {path} → {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    # ------------------------------------------------------------------ helpers
    def search(
        self,
        query: str,
        index: str = "table_search_index",
        size: int = 20,
        filters: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"q": query or "*", "index": index, "size": size}
        if filters:
            params["query_filter"] = filters
        return self.get("/search/query", params=params)

    def get_entity_by_fqn(self, entity_type: str, fqn: str, fields: str | None = None) -> Any:
        path = f"/{entity_type}/name/{quote(fqn, safe='')}"
        params = {"fields": fields} if fields else None
        return self.get(path, params=params)

    def get_entity_by_id(self, entity_type: str, entity_id: str, fields: str | None = None) -> Any:
        params = {"fields": fields} if fields else None
        return self.get(f"/{entity_type}/{entity_id}", params=params)

    def get_lineage(
        self,
        entity_type: str,
        entity_id: str,
        upstream_depth: int = 3,
        downstream_depth: int = 3,
    ) -> Any:
        return self.get(
            f"/lineage/{entity_type}/{entity_id}",
            params={"upstreamDepth": upstream_depth, "downstreamDepth": downstream_depth},
        )


def httpx_json_dumps(obj: Any) -> bytes:
    import json

    return json.dumps(obj).encode("utf-8")


def _clean(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if not params:
        return None
    return {k: v for k, v in params.items() if v is not None}


@lru_cache(maxsize=1)
def get_client() -> OpenMetadataClient:
    cfg = get_config()
    return OpenMetadataClient(cfg.openmetadata_host, cfg.openmetadata_jwt, cfg.request_timeout)
