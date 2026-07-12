import os


class Config:
    __slots__ = ("openmetadata_host", "openmetadata_jwt", "bearer_token", "request_timeout")

    def __init__(self) -> None:
        self.openmetadata_host: str = os.environ["OPENMETADATA_HOST"].rstrip("/")
        self.openmetadata_jwt: str = os.environ["OPENMETADATA_JWT"]
        self.bearer_token: str = os.environ["MCP_BEARER_TOKEN"]
        self.request_timeout: float = float(os.environ.get("REQUEST_TIMEOUT", "15"))


_CONFIG: Config | None = None


def get_config() -> Config:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = Config()
    return _CONFIG
