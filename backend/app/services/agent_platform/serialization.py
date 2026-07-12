"""JSON-safe serialization helpers for Agent Platform snapshots."""
from __future__ import annotations

from typing import Any


def json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def json_safe_row(row) -> dict[str, Any]:
    return json_safe(
        {column.name: getattr(row, column.name) for column in row.__table__.columns}
    )
