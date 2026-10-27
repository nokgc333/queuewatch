"""JSON の構造化ログと、リクエスト ID・アクセスログのテスト。"""

from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.logging_config import JsonFormatter, request_id_var


def _format(record: logging.LogRecord) -> dict[str, object]:
    return json.loads(JsonFormatter().format(record))  # type: ignore[no-any-return]


def _record(
    message: str = "hello", level: int = logging.INFO, **extra: object
) -> logging.LogRecord:
    record = logging.LogRecord("queuewatch.test", level, __file__, 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class TestJsonFormatter:
    def test_a_record_is_one_json_object_with_the_core_fields(self) -> None:
        payload = _format(_record("job started"))

        assert payload["message"] == "job started"
        assert payload["level"] == "INFO"
        assert payload["logger"] == "queuewatch.test"
        assert str(payload["timestamp"]).endswith("Z")

    def test_extra_fields_are_included(self) -> None:
        payload = _format(_record("x", job_id=7, status="dead"))

        assert payload["job_id"] == 7
        assert payload["status"] == "dead"

    def test_the_request_id_of_the_current_request_is_attached(self) -> None:
        token = request_id_var.set("abc-123")
        try:
            payload = _format(_record("x"))
        finally:
            request_id_var.reset(token)

        assert payload["request_id"] == "abc-123"

    def test_without_a_request_the_field_is_absent(self) -> None:
        assert "request_id" not in _format(_record("x"))

    def test_an_exception_is_included_as_text(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                "q", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
            )

        assert "ValueError: boom" in str(_format(record)["exc_info"])

    def test_newlines_in_a_message_cannot_forge_a_second_log_line(self) -> None:
        output = JsonFormatter().format(_record('a\n{"level": "CRITICAL"}'))

        assert "\n" not in output
        assert json.loads(output)["level"] == "INFO"


class TestRequestId:
    def test_a_response_always_carries_a_request_id(self, client: TestClient) -> None:
        assert client.get("/healthz").headers["X-Request-ID"]

    def test_a_valid_id_from_the_caller_is_kept(self, client: TestClient) -> None:
        response = client.get("/healthz", headers={"X-Request-ID": "trace-0001.abc"})

        assert response.headers["X-Request-ID"] == "trace-0001.abc"

    @pytest.mark.parametrize("bad", ["a b", "x" * 65, "a\tb", "<script>", ""])
    def test_an_unsafe_id_is_replaced(self, client: TestClient, bad: str) -> None:
        response = client.get("/healthz", headers={"X-Request-ID": bad})

        assert response.headers["X-Request-ID"] != bad
        assert response.headers["X-Request-ID"]

    def test_each_request_gets_its_own_id(self, client: TestClient) -> None:
        first = client.get("/healthz").headers["X-Request-ID"]
        second = client.get("/healthz").headers["X-Request-ID"]

        assert first != second


class TestAccessLog:
    def test_a_request_is_logged_with_method_path_status_and_duration(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="queuewatch.access"):
            client.get("/jobs", headers={"X-Request-ID": "req-1"})

        record = next(r for r in caplog.records if r.name == "queuewatch.access")
        fields = record.__dict__
        assert (fields["method"], fields["path"], fields["status"]) == ("GET", "/jobs", 200)
        assert fields["duration_ms"] >= 0
        assert fields["request_id"] == "req-1"

    def test_the_log_never_contains_the_authorization_header_or_the_query(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="queuewatch.access"):
            client.get("/jobs?status=dead", headers={"Authorization": "Bearer secret-token-xyz"})

        records = [r for r in caplog.records if r.name == "queuewatch.access"]
        text = " ".join(str(r.__dict__) for r in records)
        assert "secret-token-xyz" not in text
        assert "status=dead" not in text

    def test_the_health_check_is_not_logged_to_keep_the_noise_down(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger="queuewatch.access"):
            client.get("/healthz")

        assert [r for r in caplog.records if r.name == "queuewatch.access"] == []
