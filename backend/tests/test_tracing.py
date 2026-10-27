"""OpenTelemetry のトレースのテスト(メモリ上のエクスポーターで確かめる)。"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.tracing import setup_tracing, tracing_endpoint


@pytest.fixture()
def exporter() -> Iterator[InMemorySpanExporter]:
    yield InMemorySpanExporter()


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/jobs/{job_id}")
    def read(job_id: int) -> dict[str, int]:
        return {"id": job_id}

    return app


def test_a_request_produces_a_span_named_after_the_route(
    exporter: InMemorySpanExporter,
) -> None:
    app = _app()
    setup_tracing(app, exporter=exporter)

    TestClient(app).get("/jobs/5")

    names = [s.name for s in exporter.get_finished_spans()]
    assert any("/jobs/{job_id}" in n for n in names)


def test_the_service_name_is_queuewatch(exporter: InMemorySpanExporter) -> None:
    app = _app()
    setup_tracing(app, exporter=exporter)

    TestClient(app).get("/jobs/1")

    span = exporter.get_finished_spans()[0]
    assert span.resource.attributes["service.name"] == "queuewatch-api"


def test_tracing_is_off_unless_an_endpoint_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    assert tracing_endpoint() is None


def test_the_endpoint_is_read_from_the_standard_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")

    assert tracing_endpoint() == "http://collector:4318"


@pytest.mark.parametrize("value", ["ftp://x", "collector:4318", "http://"])
def test_a_bad_endpoint_is_refused(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", value)

    with pytest.raises(ValueError, match="OTEL_EXPORTER_OTLP_ENDPOINT"):
        tracing_endpoint()


def test_the_worker_tracing_is_off_without_an_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.tracing import setup_worker_tracing

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    assert setup_worker_tracing() is False


def test_the_worker_starts_tracing_when_a_process_starts() -> None:
    from celery.signals import worker_process_init

    from app import worker

    receivers = [r() if callable(r) else r for _, r in worker_process_init.receivers]

    assert worker._start_worker_tracing in receivers
