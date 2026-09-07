"""backend/tests/test_stats_api.py（GET /stats/*、FR-005/FR-008）。"""

from __future__ import annotations

import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Job, RetryLog, WorkerStat


def test_get_utilization_stats_empty(client: TestClient) -> None:
    response = client.get("/stats/utilization")

    assert response.status_code == 200
    assert response.json() == []


def test_get_utilization_stats_returns_per_worker_value(
    client: TestClient, db_session: Session
) -> None:
    window_start = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    stat = WorkerStat(
        worker_name="celery@worker1",
        processed_count=4,
        failed_count=0,
        total_busy_seconds=20.0,
        window_start=window_start,
        window_end=window_start + datetime.timedelta(seconds=40),
    )
    db_session.add(stat)
    db_session.commit()

    response = client.get("/stats/utilization")

    assert response.status_code == 200
    body = response.json()
    assert body == [{"worker_name": "celery@worker1", "utilization": 0.5}]


def test_get_duration_stats_empty(client: TestClient) -> None:
    response = client.get("/stats/duration")

    assert response.status_code == 200
    assert response.json() == []


def test_get_duration_stats_builds_histogram(client: TestClient, db_session: Session) -> None:
    started = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    job1 = Job(
        name="J1",
        priority="normal",
        status="success",
        started_at=started,
        finished_at=started + datetime.timedelta(seconds=5),
    )
    job2 = Job(
        name="J2",
        priority="normal",
        status="success",
        started_at=started,
        finished_at=started + datetime.timedelta(seconds=10),
    )
    db_session.add_all([job1, job2])
    db_session.commit()

    response = client.get("/stats/duration")

    assert response.status_code == 200
    bins = response.json()
    assert len(bins) == 10
    total_count = sum(b["count"] for b in bins)
    assert total_count == 2


def test_get_duration_stats_ignores_unfinished_jobs(
    client: TestClient, db_session: Session
) -> None:
    job = Job(name="J_UNFINISHED", priority="normal", status="running")
    db_session.add(job)
    db_session.commit()

    response = client.get("/stats/duration")

    assert response.status_code == 200
    assert response.json() == []


def test_get_error_stats_empty(client: TestClient) -> None:
    response = client.get("/stats/errors")

    assert response.status_code == 200
    assert response.json() == []


def test_get_error_stats_counts_error_messages(client: TestClient, db_session: Session) -> None:
    job = Job(name="J_ERR", priority="normal", status="dead")
    db_session.add(job)
    db_session.commit()

    db_session.add_all(
        [
            RetryLog(
                job_id=job.id,
                attempt_number=1,
                status="failed",
                error_message="Simulated render failure (license server timeout)",
            ),
            RetryLog(
                job_id=job.id,
                attempt_number=2,
                status="failed",
                error_message="Simulated render failure (license server timeout)",
            ),
            RetryLog(job_id=job.id, attempt_number=3, status="success", error_message=None),
        ]
    )
    db_session.commit()

    response = client.get("/stats/errors")

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "error_message": "Simulated render failure (license server timeout)",
            "count": 2,
        }
    ]
