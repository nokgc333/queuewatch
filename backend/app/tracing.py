"""OpenTelemetry のトレース。`OTEL_EXPORTER_OTLP_ENDPOINT` を設定したときだけ有効になる。"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)

ENDPOINT_VARIABLE = "OTEL_EXPORTER_OTLP_ENDPOINT"
API_SERVICE_NAME = "queuewatch-api"
WORKER_SERVICE_NAME = "queuewatch-worker"


def tracing_endpoint() -> str | None:
    raw = os.environ.get(ENDPOINT_VARIABLE, "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{ENDPOINT_VARIABLE} must be an http or https URL, got '{raw}'")
    return raw


def _provider(service_name: str, exporter: SpanExporter, simple: bool) -> TracerProvider:
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    processor = SimpleSpanProcessor(exporter) if simple else BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    return provider


def setup_tracing(app: FastAPI, exporter: SpanExporter | None = None) -> bool:
    """API のトレースを有効にする。有効にしたら True。exporter を渡すと(テスト用)、同期で送る。"""
    simple = exporter is not None
    if exporter is None:
        endpoint = tracing_endpoint()
        if endpoint is None:
            return False
        exporter = OTLPSpanExporter(endpoint=endpoint.rstrip("/") + "/v1/traces")
    provider = _provider(API_SERVICE_NAME, exporter, simple)
    trace.set_tracer_provider(provider) if not simple else None
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    return True


def setup_worker_tracing() -> bool:
    """ワーカーのプロセス起動時に、Celery のトレースを有効にする。"""
    endpoint = tracing_endpoint()
    if endpoint is None:
        return False
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    provider = _provider(
        WORKER_SERVICE_NAME,
        OTLPSpanExporter(endpoint=endpoint.rstrip("/") + "/v1/traces"),
        simple=False,
    )
    trace.set_tracer_provider(provider)
    CeleryInstrumentor().instrument(tracer_provider=provider)  # type: ignore[no-untyped-call]
    return True
