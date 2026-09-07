"""backend/tests/test_jobs.py（TC-001〜003, TC-013相当、仕様書§12.4）。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient


def test_create_job_returns_201_with_pending_then_success(client: TestClient) -> None:
    """POST /jobsはジョブを登録し、eagerモードでは即座に処理が完了する。"""
    response = client.post("/jobs", json={"name": "SHOT010_render", "priority": "high"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "SHOT010_render"
    assert body["priority"] == "high"
    assert body["status"] in {"pending", "running", "success", "retrying", "dead"}


def test_create_job_defaults_priority_to_normal(client: TestClient) -> None:
    response = client.post("/jobs", json={"name": "SHOT020_render"})

    assert response.status_code == 201
    assert response.json()["priority"] == "normal"


def test_create_job_rejects_invalid_priority(client: TestClient) -> None:
    response = client.post("/jobs", json={"name": "SHOT030_render", "priority": "urgent"})

    assert response.status_code == 422


def test_create_job_rejects_missing_name(client: TestClient) -> None:
    response = client.post("/jobs", json={"priority": "high"})

    assert response.status_code == 422


def test_create_job_returns_503_when_broker_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Redis接続不可時は503を返す（仕様書§2.7, §5.4 ERR-BROKER-UNAVAILABLE）。"""

    def _raise_connection_error(*args: Any, **kwargs: Any) -> Any:
        raise ConnectionError("broker unreachable")

    monkeypatch.setattr("app.routers.jobs.process_render_job.apply_async", _raise_connection_error)

    response = client.post("/jobs", json={"name": "SHOT040_render", "priority": "low"})

    assert response.status_code == 503
    assert response.json()["title"] == "Queue service unavailable"


def test_create_job_returns_503_on_celery_runtime_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """実機検証で確認: celery.backends.asynchronousは再接続上限到達時に
    素のRuntimeErrorを送出する（redis-pyのConnectionErrorではラップされない
    ケースがあるため、広めの例外集合で捕捉する必要がある）。
    """

    def _raise_runtime_error(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            "Retry limit exceeded while trying to reconnect to the Celery result store backend."
        )

    monkeypatch.setattr("app.routers.jobs.process_render_job.apply_async", _raise_runtime_error)

    response = client.post("/jobs", json={"name": "SHOT041_render", "priority": "low"})

    assert response.status_code == 503
    assert response.json()["title"] == "Queue service unavailable"


def test_list_jobs_returns_all_jobs(client: TestClient) -> None:
    client.post("/jobs", json={"name": "JOB_A", "priority": "high"})
    client.post("/jobs", json={"name": "JOB_B", "priority": "low"})

    response = client.get("/jobs")

    assert response.status_code == 200
    names = {job["name"] for job in response.json()}
    assert names == {"JOB_A", "JOB_B"}


def test_list_jobs_filters_by_status(client: TestClient) -> None:
    client.post("/jobs", json={"name": "JOB_C", "priority": "normal"})

    response = client.get("/jobs", params={"status": "no_such_status"})

    assert response.status_code == 200
    assert response.json() == []


def test_list_jobs_filters_by_priority(client: TestClient) -> None:
    client.post("/jobs", json={"name": "JOB_D", "priority": "high"})
    client.post("/jobs", json={"name": "JOB_E", "priority": "low"})

    response = client.get("/jobs", params={"priority": "high"})

    assert response.status_code == 200
    names = {job["name"] for job in response.json()}
    assert names == {"JOB_D"}


def test_get_job_detail_includes_retry_logs(client: TestClient) -> None:
    create_response = client.post("/jobs", json={"name": "JOB_F", "priority": "normal"})
    job_id = create_response.json()["id"]

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == job_id
    assert "retry_logs" in body


def test_get_job_detail_returns_404_for_missing_job(client: TestClient) -> None:
    response = client.get("/jobs/999999")

    assert response.status_code == 404
    assert response.json()["title"] == "Job 999999 not found"


def test_delete_job_removes_job(client: TestClient) -> None:
    create_response = client.post("/jobs", json={"name": "JOB_G", "priority": "normal"})
    job_id = create_response.json()["id"]

    delete_response = client.delete(f"/jobs/{job_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/jobs/{job_id}")
    assert get_response.status_code == 404


def test_delete_job_returns_404_for_missing_job(client: TestClient) -> None:
    response = client.delete("/jobs/999999")

    assert response.status_code == 404
