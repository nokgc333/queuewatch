"""認証(local / token)とロールのテスト。"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.auth import load_auth_settings

TOKENS = "viewer=view-token-0001,editor=edit-token-0002,admin=admin-token-0003"
READ_PATHS = ["/jobs", "/workers/status", "/stats/utilization", "/stats/duration", "/stats/errors"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def token_mode(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("QUEUEWATCH_AUTH_MODE", "token")
    monkeypatch.setenv("QUEUEWATCH_API_TOKENS", TOKENS)
    yield


class TestLocalMode:
    def test_everything_is_allowed_without_credentials_by_default(self, client: TestClient) -> None:
        assert client.get("/jobs").status_code == 200
        assert client.post("/jobs", json={"name": "r"}).status_code == 201

    def test_an_unknown_mode_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QUEUEWATCH_AUTH_MODE", "open")

        with pytest.raises(ValueError, match="QUEUEWATCH_AUTH_MODE"):
            load_auth_settings()


@pytest.mark.usefixtures("token_mode")
class TestTokenMode:
    @pytest.mark.parametrize("path", READ_PATHS)
    def test_reads_without_a_token_are_401(self, client: TestClient, path: str) -> None:
        response = client.get(path)

        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"

    def test_submitting_a_job_without_a_token_is_rejected_and_nothing_is_created(
        self, client: TestClient
    ) -> None:
        assert client.post("/jobs", json={"name": "r"}).status_code == 401
        assert client.get("/jobs", headers=_bearer("view-token-0001")).json() == []

    def test_a_wrong_token_is_401(self, client: TestClient) -> None:
        assert client.get("/jobs", headers=_bearer("nope-nope-nope-1")).status_code == 401

    @pytest.mark.parametrize("path", READ_PATHS)
    def test_a_viewer_can_read(self, client: TestClient, path: str) -> None:
        assert client.get(path, headers=_bearer("view-token-0001")).status_code == 200

    def test_a_viewer_cannot_submit_or_delete(self, client: TestClient) -> None:
        viewer = _bearer("view-token-0001")

        assert client.post("/jobs", json={"name": "r"}, headers=viewer).status_code == 403
        assert client.delete("/jobs/1", headers=viewer).status_code == 403

    def test_an_editor_can_submit_but_not_delete(self, client: TestClient) -> None:
        editor = _bearer("edit-token-0002")

        created = client.post("/jobs", json={"name": "r"}, headers=editor)

        assert created.status_code == 201
        assert client.delete(f"/jobs/{created.json()['id']}", headers=editor).status_code == 403

    def test_an_admin_can_delete(self, client: TestClient) -> None:
        editor = _bearer("edit-token-0002")
        job_id = client.post("/jobs", json={"name": "r"}, headers=editor).json()["id"]

        assert (
            client.delete(f"/jobs/{job_id}", headers=_bearer("admin-token-0003")).status_code == 204
        )

    def test_permission_is_checked_before_the_job_exists(self, client: TestClient) -> None:
        response = client.delete("/jobs/9999", headers=_bearer("view-token-0001"))

        assert response.status_code == 403

    def test_the_health_check_stays_public(self, client: TestClient) -> None:
        assert client.get("/healthz").status_code == 200

    def test_a_non_bearer_scheme_is_401(self, client: TestClient) -> None:
        response = client.get("/jobs", headers={"Authorization": "Basic dXNlcjpwYXNz"})

        assert response.status_code == 401


class TestTokenSettings:
    @pytest.fixture(autouse=True)
    def mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QUEUEWATCH_AUTH_MODE", "token")

    @pytest.mark.parametrize(
        ("tokens", "message"),
        [
            ("", "at least one token"),
            ("viewer", "role=token"),
            ("root=abcdefghijkl", "unknown role"),
            ("viewer=short", "at least 12"),
            ("viewer=abcdefghijkl,admin=abcdefghijkl", "must not reuse"),
        ],
    )
    def test_bad_token_settings_are_refused(
        self, monkeypatch: pytest.MonkeyPatch, tokens: str, message: str
    ) -> None:
        monkeypatch.setenv("QUEUEWATCH_API_TOKENS", tokens)

        with pytest.raises(ValueError, match=message):
            load_auth_settings()

    def test_bad_settings_stop_the_application_at_startup(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.main import app

        monkeypatch.setenv("QUEUEWATCH_API_TOKENS", "")

        with pytest.raises(ValueError):
            with TestClient(app):
                pass
