"""ジョブ投入のレート制限と、本文の大きさの上限のテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import rate_limit
from app.body_limit import MAX_BODY_BYTES


@pytest.fixture(autouse=True)
def fresh_limiter() -> None:
    rate_limit.reset()


class TestRateLimit:
    def test_submissions_over_the_write_budget_get_429_with_retry_after(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QUEUEWATCH_RATE_LIMIT_WRITE_PER_MINUTE", "2")

        responses = [client.post("/jobs", json={"name": f"r{i}"}) for i in range(4)]

        assert [r.status_code for r in responses] == [201, 201, 429, 429]
        assert int(responses[2].headers["retry-after"]) >= 1
        assert responses[2].headers["content-type"] == "application/problem+json"

    def test_reads_have_a_separate_budget(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QUEUEWATCH_RATE_LIMIT_WRITE_PER_MINUTE", "1")
        monkeypatch.setenv("QUEUEWATCH_RATE_LIMIT_READ_PER_MINUTE", "3")
        client.post("/jobs", json={"name": "r"})

        assert [client.get("/jobs").status_code for _ in range(4)] == [200, 200, 200, 429]

    def test_the_health_check_is_not_limited(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QUEUEWATCH_RATE_LIMIT_READ_PER_MINUTE", "1")

        assert [client.get("/healthz").status_code for _ in range(3)] == [200, 200, 200]

    def test_the_window_expires(self) -> None:
        limiter = rate_limit.SlidingWindowLimiter()

        assert limiter.check("k", limit=1, now=0.0) == 0
        assert limiter.check("k", limit=1, now=10.0) > 0
        assert limiter.check("k", limit=1, now=61.0) == 0

    @pytest.mark.parametrize("value", ["0", "-1", "abc"])
    def test_a_bad_limit_setting_is_refused(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv("QUEUEWATCH_RATE_LIMIT_WRITE_PER_MINUTE", value)

        with pytest.raises(ValueError, match="positive integer"):
            rate_limit.load_limits()


class TestPayloadLimits:
    def test_a_body_over_the_limit_is_413(self, client: TestClient) -> None:
        body = '{"name": "r", "pad": "' + "x" * MAX_BODY_BYTES + '"}'

        response = client.post("/jobs", content=body, headers={"Content-Type": "application/json"})

        assert response.status_code == 413
        assert response.headers["content-type"] == "application/problem+json"

    def test_a_body_exactly_at_the_limit_is_not_rejected_for_size(self, client: TestClient) -> None:
        prefix = '{"name": "r", "priority": "normal", "p": "'
        body = prefix + "x" * (MAX_BODY_BYTES - len(prefix) - 2) + '"}'
        assert len(body) == MAX_BODY_BYTES

        response = client.post("/jobs", content=body, headers={"Content-Type": "application/json"})

        assert response.status_code == 422

    def test_a_missing_content_length_is_411(self, client: TestClient) -> None:
        def chunks():  # type: ignore[no-untyped-def]
            yield b'{"name": "r"}'

        response = client.post(
            "/jobs", content=chunks(), headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 411

    def test_a_non_numeric_content_length_is_400(self, client: TestClient) -> None:
        response = client.post(
            "/jobs",
            content=b'{"name": "r"}',
            headers={"Content-Type": "application/json", "Content-Length": "abc"},
        )

        assert response.status_code == 400

    def test_unknown_fields_in_a_job_are_rejected(self, client: TestClient) -> None:
        assert client.post("/jobs", json={"name": "r", "admin": True}).status_code == 422

    def test_reads_are_not_subject_to_the_body_rule(self, client: TestClient) -> None:
        assert client.get("/jobs").status_code == 200
