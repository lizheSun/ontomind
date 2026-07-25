"""API v1 route aggregation (legacy shim).

Prefer :mod:`app.api.v1.router.api_router` — that is the current canonical
aggregator. This module exists purely so imports of ``app.api.api_router`` in
older callsites continue to work.
"""

from app.api.v1.router import api_router  # noqa: F401

__all__ = ["api_router"]