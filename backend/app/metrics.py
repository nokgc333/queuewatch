"""Prometheus 形式のメトリクス。

- HTTP のメトリクス(件数・所要時間)は、API のプロセス内で数える。ラベルはルートのテンプレート
  (`/jobs/{job_id}`)で、未知のパスは `unmatched` に集約する(ラベルの数を増やさせない)。
- ジョブのメトリクスは、スクレイプのたびに DB から数える。ワーカーは別プロセスなので、
  プロセス内のカウンターでは、ワーカーの処理が見えないため。
"""

from __future__ import annotations

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.priority_queue import PRIORITY_QUEUE_MAP
from app.models import Job

JOB_STATUSES = ("pending", "running", "retrying", "success", "dead", "paused", "cancelled")
UNMATCHED_ROUTE = "unmatched"
CONTENT_TYPE = CONTENT_TYPE_LATEST

http_registry = CollectorRegistry()
HTTP_REQUESTS = Counter(
    "queuewatch_http_requests_total",
    "HTTP requests by method, route template and status",
    ["method", "route", "status"],
    registry=http_registry,
)
HTTP_DURATION = Histogram(
    "queuewatch_http_request_duration_seconds",
    "HTTP request duration by route template",
    ["route"],
    registry=http_registry,
)


def reset_http_metrics() -> None:
    """HTTP のメトリクスを、空に戻す(テストの独立のため)。"""
    HTTP_REQUESTS.clear()
    HTTP_DURATION.clear()


def observe_request(method: str, route: str, status: int, seconds: float) -> None:
    HTTP_REQUESTS.labels(method=method, route=route, status=str(status)).inc()
    HTTP_DURATION.labels(route=route).observe(seconds)


def _job_registry(db: Session) -> CollectorRegistry:
    registry = CollectorRegistry()
    by_status = Gauge("queuewatch_jobs", "Jobs by status", ["status"], registry=registry)
    by_priority = Gauge(
        "queuewatch_jobs_by_priority", "Jobs by priority", ["priority"], registry=registry
    )
    retries = Gauge(
        "queuewatch_job_retries", "Total retry attempts across all jobs", registry=registry
    )
    status_counts = dict(db.query(Job.status, func.count(Job.id)).group_by(Job.status).all())
    for status in JOB_STATUSES:
        by_status.labels(status=status).set(status_counts.get(status, 0))
    priority_counts = dict(db.query(Job.priority, func.count(Job.id)).group_by(Job.priority).all())
    for priority in PRIORITY_QUEUE_MAP:
        by_priority.labels(priority=priority).set(priority_counts.get(priority, 0))
    retries.set(db.query(func.coalesce(func.sum(Job.retry_count), 0)).scalar() or 0)
    return registry


def render_metrics(db: Session) -> bytes:
    return generate_latest(_job_registry(db)) + generate_latest(http_registry)
