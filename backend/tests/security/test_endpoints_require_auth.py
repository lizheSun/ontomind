"""Auth-gate: every /data-platform and /knowledge-base endpoint returns 401
when accessed without a Bearer token."""
from __future__ import annotations

import io


def _resolve_dummy_path(path: str) -> str:
    """Fill in path params with dummy values so we still exercise routing."""
    for placeholder in (
        "{source_id}",
        "{session_id}",
        "{message_id}",
        "{saved_id}",
        "{id}",
    ):
        path = path.replace(placeholder, "1")
    return path


def _protected_routes(app) -> list[tuple[str, str]]:
    """Enumerate (method, path) for every DP or KB endpoint. HEAD/OPTIONS
    are excluded — starlette does not require auth for those."""
    routes: list[tuple[str, str]] = []
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None)
        if not path or not methods:
            continue
        if not (
            "/api/v1/data-platform" in path or "/api/v1/knowledge-base" in path
        ):
            continue
        for m in methods:
            if m in {"HEAD", "OPTIONS"}:
                continue
            routes.append((m, path))
    return routes


def test_all_dp_and_kb_endpoints_require_auth(anon_client):
    from app.main import app

    routes = _protected_routes(app)
    assert len(routes) >= 20, f"expected many protected routes, got {len(routes)}"

    for method, path in routes:
        url = _resolve_dummy_path(path)
        # Upload endpoint needs a file field to reach auth; hit it without any
        # multipart body — auth still checks Header first.
        kwargs = {}
        if method == "POST" and "/documents/upload" in url:
            kwargs = {
                "files": {"file": ("x", io.BytesIO(b"x"), "text/plain")},
                "data": {"title_zh": "t", "library_id": "1"},
            }
        elif method in {"POST", "PUT", "PATCH"}:
            kwargs = {"json": {}}
        resp = anon_client.request(method, url, **kwargs)
        assert resp.status_code == 401, (
            f"{method} {url} did not return 401 without token "
            f"(got {resp.status_code}: {resp.text[:200]})"
        )


def test_dp_sources_list_401_without_token(anon_client):
    r = anon_client.get("/api/v1/data-platform/sources")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] in {"UNAUTHORIZED", "INVALID_TOKEN"}


def test_kb_libraries_list_401_without_token(anon_client):
    r = anon_client.get("/api/v1/knowledge-base/libraries")
    assert r.status_code == 401


def test_dp_bad_token_401(anon_client):
    r = anon_client.get(
        "/api/v1/data-platform/sources", headers={"Authorization": "Bearer garbage"}
    )
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_TOKEN"


def test_kb_bad_scheme_401(anon_client):
    r = anon_client.get(
        "/api/v1/knowledge-base/libraries", headers={"Authorization": "Basic zzz"}
    )
    assert r.status_code == 401
