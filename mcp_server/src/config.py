"""Config: env vars for parameter names, SSM SecureString for the secrets themselves.

Fetching both secrets is done in a single ``GetParameters`` batch call on first access,
then cached for the life of the Lambda container. boto3 is bundled in the Lambda Python
runtime — not in requirements.txt.
"""
import os


class Config:
    __slots__ = ("openmetadata_host", "openmetadata_jwt", "bearer_token", "request_timeout")

    def __init__(self) -> None:
        self.openmetadata_host: str = os.environ["OPENMETADATA_HOST"].rstrip("/")
        self.request_timeout: float = float(os.environ.get("REQUEST_TIMEOUT", "15"))

        jwt_env = os.environ.get("OPENMETADATA_JWT")
        bearer_env = os.environ.get("MCP_BEARER_TOKEN")
        if jwt_env and bearer_env:
            self.openmetadata_jwt = jwt_env
            self.bearer_token = bearer_env
        else:
            self.openmetadata_jwt, self.bearer_token = _fetch_secrets()


def _fetch_secrets() -> tuple[str, str]:
    import boto3
    jwt_param = os.environ["OPENMETADATA_JWT_PARAM"]
    bearer_param = os.environ["MCP_BEARER_TOKEN_PARAM"]
    ssm = boto3.client("ssm")
    resp = ssm.get_parameters(Names=[jwt_param, bearer_param], WithDecryption=True)
    values = {p["Name"]: p["Value"] for p in resp["Parameters"]}
    return values[jwt_param], values[bearer_param]


_CONFIG: Config | None = None


def get_config() -> Config:
    global _CONFIG
    if _CONFIG is None:
        _CONFIG = Config()
    return _CONFIG
