"""実レンダラー(RENDERER=blender)での、投入から実行・出力までの流れのテスト。Blender は偽の実行ファイル。"""

from __future__ import annotations

import stat
import sys
import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.models import Job
from app.tasks import process_render_job
from app.worker import task_soft_time_limit, task_time_limit

GOOD = """
import sys, pathlib
args = sys.argv
out = pathlib.Path(args[args.index("-o") + 1])
start, end = int(args[args.index("-s") + 1]), int(args[args.index("-e") + 1])
out.parent.mkdir(parents=True, exist_ok=True)
for f in range(start, end + 1):
    print(f"Fra:{f} Mem:1M", flush=True)
    (out.parent / f"frame_{f:04d}.png").write_bytes(b"PNG")
"""
BAD = """
import sys
print("Error: Cannot read file", flush=True)
sys.exit(2)
"""


def _fake(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake_blender.py"
    script.write_text("#!" + sys.executable + "\n" + textwrap.dedent(body), encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


@pytest.fixture()
def blender_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    scenes = tmp_path / "scenes"
    scenes.mkdir()
    (scenes / "shot.blend").write_bytes(b"BLENDER")
    monkeypatch.setattr(settings, "RENDERER", "blender")
    monkeypatch.setattr(settings, "RENDER_SCENE_ROOT", str(scenes))
    monkeypatch.setattr(settings, "RENDER_OUTPUT_ROOT", str(tmp_path / "renders"))
    monkeypatch.setattr(settings, "RENDER_TIMEOUT_SECONDS", 20.0)
    monkeypatch.setattr(settings, "BLENDER_PATH", str(_fake(tmp_path, GOOD)))
    return tmp_path


def _submit(client: TestClient, **fields: object) -> dict:  # type: ignore[type-arg]
    return client.post("/jobs", json={"name": "r", "scene": "shot.blend", **fields}).json()


@pytest.mark.usefixtures("blender_mode")
class TestSubmission:
    def test_a_job_keeps_its_scene_and_frame_range(self, client: TestClient) -> None:
        job = _submit(client, frame_start=2, frame_end=4)

        assert (job["scene"], job["frame_start"], job["frame_end"]) == ("shot.blend", 2, 4)

    def test_a_job_without_a_scene_is_rejected(self, client: TestClient) -> None:
        response = client.post("/jobs", json={"name": "r"})

        assert response.status_code == 422
        assert "scene is required" in response.json()["title"]

    @pytest.mark.parametrize("scene", ["../x.blend", "/etc/passwd.blend", "none.blend", "a.txt"])
    def test_a_scene_that_is_not_allowed_is_rejected_before_queueing(
        self, client: TestClient, scene: str
    ) -> None:
        response = client.post("/jobs", json={"name": "r", "scene": scene})

        assert response.status_code == 422
        assert client.get("/jobs").json() == []

    def test_a_reversed_frame_range_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/jobs", json={"name": "r", "scene": "shot.blend", "frame_start": 5, "frame_end": 2}
        )

        assert response.status_code == 422

    def test_too_many_frames_are_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/jobs",
            json={"name": "r", "scene": "shot.blend", "frame_start": 1, "frame_end": 10_002},
        )

        assert response.status_code == 422


@pytest.mark.usefixtures("blender_mode")
class TestExecution:
    def test_a_job_renders_its_frames_and_records_the_output(
        self, client: TestClient, db_session: Session
    ) -> None:
        job_id = _submit(client, frame_start=1, frame_end=3)["id"]

        job = db_session.get(Job, job_id)
        assert job is not None
        db_session.refresh(job)
        assert job.status == "success"
        assert job.progress == 100
        assert job.output_dir is not None
        assert len(list(Path(job.output_dir).glob("frame_*.png"))) == 3

    def test_a_failing_blender_goes_through_the_normal_retry_path(
        self,
        client: TestClient,
        db_session: Session,
        blender_mode: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "BLENDER_PATH", str(_fake(blender_mode, BAD)))
        job = Job(name="r", priority="normal", status="pending", scene="shot.blend")
        db_session.add(job)
        db_session.commit()

        with pytest.raises(Exception):
            process_render_job.apply(args=[job.id]).get(propagate=True)

        db_session.refresh(job)
        assert job.status == "retrying"
        assert job.retry_count == 1
        assert "exit code 2" in (job.error_message or "")

    def test_after_the_last_retry_the_job_is_dead(
        self,
        db_session: Session,
        blender_mode: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(settings, "BLENDER_PATH", str(_fake(blender_mode, BAD)))
        job = Job(name="r", priority="normal", status="retrying", scene="shot.blend", retry_count=2)
        db_session.add(job)
        db_session.commit()

        process_render_job.apply(args=[job.id]).get(propagate=True)

        db_session.refresh(job)
        assert job.status == "dead"


class TestTimeLimits:
    def test_the_simulated_renderer_keeps_the_short_limits(self) -> None:
        config = Settings(RENDERER="simulated")

        assert (task_time_limit(config), task_soft_time_limit(config)) == (30, 25)

    def test_a_real_render_waits_longer_than_the_renderer_timeout(self) -> None:
        config = Settings(RENDERER="blender", RENDER_TIMEOUT_SECONDS=600)

        assert task_time_limit(config) == 720
        assert task_soft_time_limit(config) == 660
        assert task_soft_time_limit(config) < task_time_limit(config)

    def test_the_default_renderer_is_simulated(self) -> None:
        assert Settings().RENDERER == "simulated"
