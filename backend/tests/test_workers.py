"""backend/tests/test_workers.py（GET /workers/status、FR-003）。"""

from __future__ import annotations

import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import WorkerStat


def test_get_worker_status_returns_empty_list_when_no_stats(client: TestClient) -> None:
    response = client.get("/workers/status")

    assert response.status_code == 200
    assert response.json() == []


def test_get_worker_status_computes_utilization(client: TestClient, db_session: Session) -> None:
    window_start = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    window_end = window_start + datetime.timedelta(seconds=100)
    stat = WorkerStat(
        worker_name="celery@worker1",
        processed_count=10,
        failed_count=1,
        total_busy_seconds=50.0,
        window_start=window_start,
        window_end=window_end,
    )
    db_session.add(stat)
    db_session.commit()

    response = client.get("/workers/status")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["worker_name"] == "celery@worker1"
    assert body[0]["processed_count"] == 10
    assert body[0]["failed_count"] == 1
    assert body[0]["utilization"] == 0.5


def test_get_worker_status_uses_latest_window_per_worker(
    client: TestClient, db_session: Session
) -> None:
    older = WorkerStat(
        worker_name="celery@worker1",
        processed_count=1,
        failed_count=0,
        total_busy_seconds=1.0,
        window_start=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        window_end=datetime.datetime(2026, 1, 1, 0, 1, tzinfo=datetime.timezone.utc),
    )
    newer = WorkerStat(
        worker_name="celery@worker1",
        processed_count=99,
        failed_count=2,
        total_busy_seconds=30.0,
        window_start=datetime.datetime(2026, 1, 2, tzinfo=datetime.timezone.utc),
        window_end=datetime.datetime(2026, 1, 2, 0, 1, tzinfo=datetime.timezone.utc),
    )
    db_session.add_all([older, newer])
    db_session.commit()

    response = client.get("/workers/status")

    body = response.json()
    assert len(body) == 1
    assert body[0]["processed_count"] == 99


def test_get_worker_status_handles_open_window_without_end(
    client: TestClient, db_session: Session
) -> None:
    """window_end=NULL(進行中のウィンドウ)でも例外にならないことを確認する。"""
    stat = WorkerStat(
        worker_name="celery@worker2",
        processed_count=3,
        failed_count=0,
        total_busy_seconds=5.0,
        window_start=datetime.datetime.now(datetime.timezone.utc),
        window_end=None,
    )
    db_session.add(stat)
    db_session.commit()

    response = client.get("/workers/status")

    assert response.status_code == 200
    assert response.json()[0]["worker_name"] == "celery@worker2"
