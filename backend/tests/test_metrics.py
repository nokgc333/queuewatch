"""Prometheus 形式の /metrics のテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import metrics
from app.models import Job, RetryLog


@pytest.fixture(autouse=True)
def clean_http_metrics() -> None:
    metrics.reset_http_metrics()


def _metric(text: str, name: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith(name)]


def test_the_endpoint_returns_the_prometheus_text_format(client: TestClient) -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# TYPE queuewatch_jobs gauge" in response.text


def test_jobs_are_counted_by_status_including_statuses_with_none(
    client: TestClient, db_session: Session
) -> None:
    for status in ("pending", "pending", "dead"):
        db_session.add(Job(name="r", priority="normal", status=status))
    db_session.commit()

    text = client.get("/metrics").text

    assert 'queuewatch_jobs{status="pending"} 2.0' in text
    assert 'queuewatch_jobs{status="dead"} 1.0' in text
    assert 'queuewatch_jobs{status="running"} 0.0' in text


def test_retries_and_dead_letters_are_reported(client: TestClient, db_session: Session) -> None:
    job = Job(name="r", priority="high", status="dead", retry_count=3)
    db_session.add(job)
    db_session.commit()
    db_session.add(RetryLog(job_id=job.id, attempt_number=1, status="failed"))
    db_session.commit()

    text = client.get("/metrics").text

    assert "queuewatch_job_retries 3.0" in text
    assert 'queuewatch_jobs_by_priority{priority="high"} 1.0' in text


def test_http_requests_are_counted_by_method_route_and_status(client: TestClient) -> None:
    client.get("/jobs")
    client.get("/jobs/9999")
    client.get("/jobs/8888")

    text = client.get("/metrics").text

    assert 'method="GET",route="/jobs",status="200"' in text
    assert 'method="GET",route="/jobs/{job_id}",status="404"} 2.0' in text


def test_the_label_is_the_route_template_not_the_raw_path(client: TestClient) -> None:
    for job_id in range(30):
        client.get(f"/jobs/{job_id + 5000}")

    text = client.get("/metrics").text

    assert "/jobs/5000" not in text


def test_unknown_paths_share_one_label_so_scanners_cannot_blow_up_the_cardinality(
    client: TestClient,
) -> None:
    for path in ("/a", "/b", "/wp-admin"):
        client.get(path)

    text = client.get("/metrics").text

    assert 'route="unmatched"' in text
    assert "/wp-admin" not in text


def test_request_duration_is_a_histogram(client: TestClient) -> None:
    client.get("/jobs")

    text = client.get("/metrics").text

    assert "# TYPE queuewatch_http_request_duration_seconds histogram" in text
    assert _metric(text, 'queuewatch_http_request_duration_seconds_count{route="/jobs"}')


@pytest.fixture()
def token_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUEUEWATCH_AUTH_MODE", "token")
    monkeypatch.setenv("QUEUEWATCH_API_TOKENS", "viewer=view-token-0001,admin=admin-token-0003")


@pytest.mark.usefixtures("token_mode")
class TestAccess:
    def test_metrics_need_a_token_in_token_mode(self, client: TestClient) -> None:
        assert client.get("/metrics").status_code == 401

    def test_a_viewer_token_is_enough_for_a_scraper(self, client: TestClient) -> None:
        response = client.get("/metrics", headers={"Authorization": "Bearer view-token-0001"})

        assert response.status_code == 200
