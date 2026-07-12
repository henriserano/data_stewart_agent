"""Lightweight tool registry and JSON schema auto-generation from Python type hints."""
from __future__ import annotations

import inspect
import types
import typing
from typing import Any, Callable


TOOLS: dict[str, dict[str, Any]] = {}


def _py_type_to_schema(py_type: Any) -> dict[str, Any]:
    if py_type is str:
        return {"type": "string"}
    if py_type is int:
        return {"type": "integer"}
    if py_type is float:
        return {"type": "number"}
    if py_type is bool:
        return {"type": "boolean"}
    if py_type is dict or typing.get_origin(py_type) is dict:
        return {"type": "object"}
    if py_type is list or typing.get_origin(py_type) is list:
        args = typing.get_args(py_type)
        return {"type": "array", "items": _py_type_to_schema(args[0]) if args else {}}
    origin = typing.get_origin(py_type)
    if origin is typing.Union or origin is types.UnionType:
        non_none = [a for a in typing.get_args(py_type) if a is not type(None)]
        if non_none:
            return _py_type_to_schema(non_none[0])
    return {}


def _schema_from_fn(fn: Callable[..., Any]) -> dict[str, Any]:
    sig = inspect.signature(fn)
    try:
        hints = typing.get_type_hints(fn)
    except Exception:
        hints = {}
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, param in sig.parameters.items():
        prop = _py_type_to_schema(hints.get(name))
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            prop["default"] = param.default
        properties[name] = prop
    return {"type": "object", "properties": properties, "required": required}


def tool(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Register a function as an MCP tool. Uses docstring first line as description."""
    doc = (fn.__doc__ or "").strip()
    description = doc.split("\n")[0] if doc else fn.__name__
    TOOLS[fn.__name__] = {
        "fn": fn,
        "description": description,
        "inputSchema": _schema_from_fn(fn),
    }
    return fn
