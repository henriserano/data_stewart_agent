import os
from functools import lru_cache

import boto3


class Config:
    def __init__(self) -> None:
        self.openmetadata_host: str = os.environ["OPENMETADATA_HOST"].rstrip("/")
        self.bearer_token: str = _resolve_secret("MCP_BEARER_TOKEN_PARAM", "MCP_BEARER_TOKEN")
        self.openmetadata_jwt: str = _resolve_secret("OPENMETADATA_JWT_PARAM", "OPENMETADATA_JWT")
        self.request_timeout: float = float(os.environ.get("REQUEST_TIMEOUT", "20"))
        self.default_page_size: int = int(os.environ.get("DEFAULT_PAGE_SIZE", "20"))


def _resolve_secret(param_env: str, inline_env: str) -> str:
    param_name = os.environ.get(param_env)
    if param_name:
        return _fetch_ssm_parameter(param_name)
    inline = os.environ.get(inline_env)
    if inline:
        return inline
    raise RuntimeError(
        f"Missing secret: set either {param_env} (SSM parameter name) or {inline_env} (raw value)."
    )


@lru_cache(maxsize=32)
def _fetch_ssm_parameter(name: str) -> str:
    ssm = boto3.client("ssm")
    resp = ssm.get_parameter(Name=name, WithDecryption=True)
    return resp["Parameter"]["Value"]


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()
