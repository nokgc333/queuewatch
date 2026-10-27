"""CORS の既定(ローカルの画面だけ)と、明示したときだけの `*` のテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.cors import DEFAULT_ORIGIN, load_allowed_origins


def _preflight(client: TestClient, origin: str):  # type: ignore[no-untyped-def]
    return client.options(
        "/jobs",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )


class TestAllowedOrigins:
    def test_the_default_is_the_local_dashboard_only(self) -> None:
        assert load_allowed_origins() == [DEFAULT_ORIGIN]
        assert DEFAULT_ORIGIN == "http://localhost:5173"

    def test_several_origins_can_be_listed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QUEUEWATCH_CORS_ORIGINS", "https://a.test, https://b.test")

        assert load_allowed_origins() == ["https://a.test", "https://b.test"]

    def test_a_wildcard_is_used_only_when_set_explicitly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QUEUEWATCH_CORS_ORIGINS", "*")

        assert load_allowed_origins() == ["*"]

    def test_a_wildcard_mixed_with_origins_is_refused(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QUEUEWATCH_CORS_ORIGINS", "*,https://a.test")

        with pytest.raises(ValueError, match="must not mix"):
            load_allowed_origins()


class TestPreflight:
    def test_the_local_dashboard_is_allowed(self, client: TestClient) -> None:
        response = _preflight(client, "http://localhost:5173")

        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"

    def test_another_origin_is_not_allowed(self, client: TestClient) -> None:
        response = _preflight(client, "https://evil.test")

        assert "access-control-allow-origin" not in response.headers

    def test_credentials_are_never_allowed(self, client: TestClient) -> None:
        response = _preflight(client, "http://localhost:5173")

        assert "access-control-allow-credentials" not in response.headers
