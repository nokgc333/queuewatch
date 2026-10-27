"""実 Blender での、投入 → 実行 → 出力ファイルの確認。

使い方(backend の venv で):
    BLENDER_APP=/Applications/Blender.app python scripts/verify_blender_render.py

結果は 1 行 1 項目の `CHECK <名前> <PASS|FAIL> <詳細>`。Celery は eager(同期)で、Redis は要らない。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
blender = Path(os.environ.get("BLENDER_APP", "/Applications/Blender.app")) / "Contents/MacOS/Blender"


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"CHECK {name} {'PASS' if ok else 'FAIL'} {detail}")


with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    (work / "scenes").mkdir()
    subprocess.run(
        [str(blender), "-b", "--factory-startup", "--python", str(ROOT / "scripts/make_sample_scene.py"),
         "--", str(work / "scenes" / "cube.blend")],
        check=True, capture_output=True,
    )
    version = subprocess.run(
        [str(blender), "-b", "--version"], capture_output=True, text=True
    ).stdout.splitlines()[0]
    print(f"BLENDER_VERSION {version}")
    os.environ.update(
        RENDERER="blender",
        BLENDER_PATH=str(blender),
        RENDER_SCENE_ROOT=str(work / "scenes"),
        RENDER_OUTPUT_ROOT=str(work / "renders"),
        CELERY_TASK_ALWAYS_EAGER="true",
        DATABASE_URL=f"sqlite:///{work / 'q.db'}",
    )
    sys.path.insert(0, str(ROOT / "backend"))

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    rejected = client.post("/jobs", json={"name": "bad", "scene": "../../etc/passwd.blend"})
    check("a_path_outside_the_scene_root_is_rejected", rejected.status_code == 422, str(rejected.status_code))

    created = client.post("/jobs", json={"name": "cube", "scene": "cube.blend", "frame_start": 1, "frame_end": 4})
    job = client.get(f"/jobs/{created.json()['id']}").json()
    check("job_reaches_success", job["status"] == "success", job["status"])
    check("progress_is_100", job["progress"] == 100, str(job["progress"]))
    frames = sorted(Path(job["output_dir"]).glob("frame_*.png")) if job["output_dir"] else []
    check("four_frames_are_written", len(frames) == 4, f"{len(frames)} files")
    check("frames_are_pngs", bool(frames) and all(f.read_bytes()[:4] == b"\x89PNG" for f in frames), "")
    check("frames_are_not_empty", bool(frames) and all(f.stat().st_size > 100 for f in frames), "")
