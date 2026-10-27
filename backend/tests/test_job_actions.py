"""ジョブの操作(キャンセル・一時停止・再開・再投入)の遷移と API のテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.domain.job_actions import ACTIONS, next_status
from app.models import Job
from app.tasks import process_render_job


class TestTransitions:
    @pytest.mark.parametrize(
        ("action", "current", "expected"),
        [
            ("cancel", "pending", "cancelled"),
            ("cancel", "retrying", "cancelled"),
            ("cancel", "paused", "cancelled"),
            ("pause", "pending", "paused"),
            ("pause", "retrying", "paused"),
            ("resume", "paused", "pending"),
            ("requeue", "dead", "pending"),
            ("requeue", "cancelled", "pending"),
        ],
    )
    def test_the_allowed_transitions(self, action: str, current: str, expected: str) -> None:
        assert next_status(action, current) == expected

    @pytest.mark.parametrize(
        ("action", "current"),
        [
            ("cancel", "running"),
            ("cancel", "success"),
            ("cancel", "dead"),
            ("cancel", "cancelled"),
            ("pause", "running"),
            ("pause", "paused"),
            ("pause", "success"),
            ("resume", "pending"),
            ("resume", "dead"),
            ("requeue", "pending"),
            ("requeue", "running"),
            ("requeue", "success"),
        ],
    )
    def test_everything_else_is_refused(self, action: str, current: str) -> None:
        assert next_status(action, current) is None

    def test_an_unknown_action_is_refused(self) -> None:
        assert next_status("explode", "pending") is None

    def test_the_four_actions_are_defined(self) -> None:
        assert set(ACTIONS) == {"cancel", "pause", "resume", "requeue"}


def _job(db: Session, status: str, **fields: object) -> Job:
    job = Job(name="r", priority="normal", status=status, **fields)  # type: ignore[arg-type]
    db.add(job)
    db.commit()
    return job


class TestApi:
    def test_cancelling_a_pending_job_marks_it_cancelled(
        self, client: TestClient, db_session: Session
    ) -> None:
        job = _job(db_session, "pending")

        response = client.post(f"/jobs/{job.id}/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        assert response.json()["finished_at"] is not None

    def test_a_running_job_cannot_be_cancelled(
        self, client: TestClient, db_session: Session
    ) -> None:
        job = _job(db_session, "running")

        response = client.post(f"/jobs/{job.id}/cancel")

        assert response.status_code == 409
        assert "running" in response.json()["title"]

    def test_pausing_keeps_the_retry_count_and_resuming_queues_it_again(
        self, client: TestClient, db_session: Session
    ) -> None:
        job = _job(db_session, "retrying", retry_count=2)

        paused = client.post(f"/jobs/{job.id}/pause").json()
        resumed = client.post(f"/jobs/{job.id}/resume").json()

        assert paused["status"] == "paused" and paused["retry_count"] == 2
        assert resumed["status"] == "success"
        assert resumed["retry_count"] == 2

    def test_requeueing_a_dead_job_resets_it_and_runs_it(
        self, client: TestClient, db_session: Session
    ) -> None:
        job = _job(db_session, "dead", retry_count=3, error_message="boom", progress=40)

        body = client.post(f"/jobs/{job.id}/requeue").json()

        assert body["status"] == "success"
        assert body["retry_count"] == 0
        assert body["error_message"] is None
        assert body["progress"] == 100

    def test_a_missing_job_is_404(self, client: TestClient) -> None:
        for action in ("cancel", "pause", "resume", "requeue"):
            assert client.post(f"/jobs/9999/{action}").status_code == 404

    def test_an_unknown_action_is_404(self, client: TestClient, db_session: Session) -> None:
        job = _job(db_session, "pending")

        assert client.post(f"/jobs/{job.id}/explode").status_code == 404

    def test_a_cancelled_job_is_not_run_by_a_worker_that_still_has_the_message(
        self, db_session: Session
    ) -> None:
        job = _job(db_session, "cancelled")

        process_render_job.apply(args=[job.id]).get(propagate=True)

        db_session.refresh(job)
        assert job.status == "cancelled"
        assert job.started_at is None

    def test_a_paused_job_is_not_run_either(self, db_session: Session) -> None:
        job = _job(db_session, "paused")

        process_render_job.apply(args=[job.id]).get(propagate=True)

        db_session.refresh(job)
        assert job.status == "paused"


@pytest.fixture()
def token_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUEUEWATCH_AUTH_MODE", "token")
    monkeypatch.setenv("QUEUEWATCH_API_TOKENS", "viewer=view-token-0001,editor=edit-token-0002")


@pytest.mark.usefixtures("token_mode")
class TestPermissions:
    def test_a_viewer_cannot_control_jobs_but_an_editor_can(
        self, client: TestClient, db_session: Session
    ) -> None:
        job = _job(db_session, "pending")
        viewer = {"Authorization": "Bearer view-token-0001"}
        editor = {"Authorization": "Bearer edit-token-0002"}

        assert client.post(f"/jobs/{job.id}/cancel", headers=viewer).status_code == 403
        assert client.post(f"/jobs/{job.id}/cancel", headers=editor).status_code == 200
