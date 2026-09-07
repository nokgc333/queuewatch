"""backend/tests/test_main.py（/healthz, セキュリティヘッダー）。"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_returns_status_ok(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["redis"] in {"ok", "unreachable"}


def test_security_headers_are_present(client: TestClient) -> None:
    response = client.get("/healthz")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
