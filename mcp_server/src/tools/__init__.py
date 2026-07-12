"""Importing this package registers every @tool-decorated function into TOOLS."""
from tools import _registry  # noqa: F401 — must be imported first
from tools import (  # noqa: F401 — side-effect imports register the tools
    discovery,
    documentation,
    lineage,
    glossary,
    golden_source,
    quality,
    governance,
)
from tools._registry import TOOLS  # re-export

__all__ = ["TOOLS"]
