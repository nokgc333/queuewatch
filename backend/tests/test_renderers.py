"""レンダラーのポート(SimulatedRenderer / BlenderRenderer)のテスト。実 Blender は使わず、偽の実行ファイルで検証する。"""

from __future__ import annotations

import os
import stat
import sys
import textwrap
from pathlib import Path

import pytest

from app.renderers import (
    BlenderRenderer,
    RenderError,
    RenderRequest,
    SceneNotAllowedError,
    SimulatedRenderer,
    build_blender_command,
    parse_progress,
    resolve_scene,
)


def _scene(root: Path, name: str = "shot.blend") -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"BLENDER")
    return path


def _fake_blender(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake_blender.py"
    script.write_text(
        "#!" + sys.executable + "\n" + textwrap.dedent(body),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


class TestResolveScene:
    def test_a_relative_path_inside_the_root_is_resolved(self, tmp_path: Path) -> None:
        scene = _scene(tmp_path, "proj/shot.blend")

        assert resolve_scene(tmp_path, "proj/shot.blend") == scene.resolve()

    @pytest.mark.parametrize(
        "name",
        ["../outside.blend", "a/../../outside.blend", "/etc/passwd.blend", "~/x.blend"],
    )
    def test_paths_that_leave_the_root_are_refused(self, tmp_path: Path, name: str) -> None:
        root = tmp_path / "root"
        root.mkdir()
        (tmp_path / "outside.blend").write_bytes(b"x")

        with pytest.raises(SceneNotAllowedError):
            resolve_scene(root, name)

    def test_a_symlink_that_points_outside_is_refused(self, tmp_path: Path) -> None:
        root = tmp_path / "root"
        root.mkdir()
        outside = _scene(tmp_path, "secret.blend")
        (root / "link.blend").symlink_to(outside)

        with pytest.raises(SceneNotAllowedError, match="outside"):
            resolve_scene(root, "link.blend")

    @pytest.mark.parametrize("name", ["shot.txt", "shot", "shot.blend.sh", "shot.BLEND1"])
    def test_only_blend_files_are_allowed(self, tmp_path: Path, name: str) -> None:
        _scene(tmp_path, name)

        with pytest.raises(SceneNotAllowedError, match=".blend"):
            resolve_scene(tmp_path, name)

    def test_a_name_that_looks_like_an_option_is_refused(self, tmp_path: Path) -> None:
        _scene(tmp_path, "-P.blend")

        with pytest.raises(SceneNotAllowedError, match="start with"):
            resolve_scene(tmp_path, "-P.blend")

    def test_a_missing_file_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(SceneNotAllowedError, match="does not exist"):
            resolve_scene(tmp_path, "none.blend")

    def test_an_uppercase_extension_is_accepted(self, tmp_path: Path) -> None:
        _scene(tmp_path, "shot.BLEND")

        assert resolve_scene(tmp_path, "shot.BLEND").name == "shot.BLEND"

    def test_a_null_byte_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(SceneNotAllowedError):
            resolve_scene(tmp_path, "a\x00.blend")


class TestBuildCommand:
    def test_the_command_is_a_list_with_the_frame_range_and_output_prefix(
        self, tmp_path: Path
    ) -> None:
        scene = _scene(tmp_path)

        command = build_blender_command("/opt/blender", scene, tmp_path / "out", 3, 9)

        assert command == [
            "/opt/blender",
            "-b",
            str(scene),
            "-noaudio",
            "-o",
            str(tmp_path / "out" / "frame_####"),
            "-F",
            "PNG",
            "-s",
            "3",
            "-e",
            "9",
            "-a",
        ]

    def test_every_argument_is_a_string(self, tmp_path: Path) -> None:
        command = build_blender_command("b", _scene(tmp_path), tmp_path, 1, 2)

        assert all(isinstance(part, str) for part in command)


class TestParseProgress:
    def test_a_frame_line_gives_the_fraction_done(self) -> None:
        assert parse_progress("Fra:5 Mem:12.00M (Peak 14.00M) | Time:00:00.50", 1, 10) == 40

    def test_the_last_frame_is_nearly_done_not_complete(self) -> None:
        assert parse_progress("Fra:10 Mem:1M", 1, 10) == 90

    def test_a_saved_line_counts_the_frame_as_done(self) -> None:
        assert parse_progress("Saved: '/tmp/out/frame_0010.png'", 1, 10) is None

    def test_other_lines_are_ignored(self) -> None:
        assert parse_progress("Blender 4.0.0", 1, 10) is None

    def test_a_frame_outside_the_range_is_clamped(self) -> None:
        assert parse_progress("Fra:99 Mem:1M", 1, 10) == 100
        assert parse_progress("Fra:0 Mem:1M", 5, 10) == 0

    def test_a_single_frame_range_works(self) -> None:
        assert parse_progress("Fra:7 Mem:1M", 7, 7) == 0


class TestBlenderRenderer:
    def _renderer(self, tmp_path: Path, script: Path, timeout: float = 20.0) -> BlenderRenderer:
        return BlenderRenderer(str(script), tmp_path / "root", tmp_path / "out", timeout)

    def _request(self, tmp_path: Path, scene: str = "shot.blend") -> RenderRequest:
        root = tmp_path / "root"
        _scene(root, scene)
        return RenderRequest(job_id=7, scene=scene, frame_start=1, frame_end=3)

    def test_a_successful_render_returns_the_output_folder_and_frame_count(
        self, tmp_path: Path
    ) -> None:
        script = _fake_blender(
            tmp_path,
            """
            import sys, pathlib
            args = sys.argv
            out = pathlib.Path(args[args.index("-o") + 1])
            start, end = int(args[args.index("-s") + 1]), int(args[args.index("-e") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            for f in range(start, end + 1):
                print(f"Fra:{f} Mem:1M", flush=True)
                (out.parent / f"frame_{f:04d}.png").write_bytes(b"PNG")
                print(f"Saved: '{out.parent}/frame_{f:04d}.png'", flush=True)
            """,
        )
        renderer = self._renderer(tmp_path, script)

        result = renderer.render(self._request(tmp_path), lambda p: None)

        assert result.frames == 3
        assert Path(result.output_dir, "frame_0001.png").exists()
        assert Path(result.output_dir).name == "job-7"

    def test_progress_is_reported_in_order_and_never_goes_backwards(self, tmp_path: Path) -> None:
        script = _fake_blender(
            tmp_path,
            """
            import sys, pathlib
            args = sys.argv
            out = pathlib.Path(args[args.index("-o") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            for f in (1, 2, 2, 3):
                print(f"Fra:{f} Mem:1M", flush=True)
                (out.parent / f"frame_{f:04d}.png").write_bytes(b"PNG")
            """,
        )
        seen: list[int] = []

        self._renderer(tmp_path, script).render(self._request(tmp_path), seen.append)

        assert seen == sorted(seen)
        assert seen[0] == 0 and seen[-1] == 66

    def test_a_non_zero_exit_raises_with_the_tail_of_the_output(self, tmp_path: Path) -> None:
        script = _fake_blender(
            tmp_path,
            """
            import sys
            print("Error: Cannot read file", flush=True)
            sys.exit(3)
            """,
        )

        with pytest.raises(RenderError, match="exit code 3.*Cannot read file"):
            self._renderer(tmp_path, script).render(self._request(tmp_path), lambda p: None)

    def test_success_without_any_output_frames_is_an_error(self, tmp_path: Path) -> None:
        script = _fake_blender(tmp_path, "print('nothing written')\n")

        with pytest.raises(RenderError, match="no frames"):
            self._renderer(tmp_path, script).render(self._request(tmp_path), lambda p: None)

    def test_a_render_that_exceeds_the_time_limit_is_killed(self, tmp_path: Path) -> None:
        script = _fake_blender(tmp_path, "import time\ntime.sleep(30)\n")

        with pytest.raises(RenderError, match="timed out after 1"):
            self._renderer(tmp_path, script, timeout=1.0).render(
                self._request(tmp_path), lambda p: None
            )

    def test_an_executable_that_does_not_exist_is_an_error(self, tmp_path: Path) -> None:
        renderer = BlenderRenderer(
            str(tmp_path / "missing"), tmp_path / "root", tmp_path / "out", 5.0
        )

        with pytest.raises(RenderError, match="could not be started"):
            renderer.render(self._request(tmp_path), lambda p: None)

    def test_a_scene_outside_the_root_never_starts_a_process(self, tmp_path: Path) -> None:
        marker = tmp_path / "ran"
        script = _fake_blender(tmp_path, f"open({str(marker)!r}, 'w').close()\n")
        renderer = self._renderer(tmp_path, script)
        (tmp_path / "root").mkdir(exist_ok=True)

        with pytest.raises(SceneNotAllowedError):
            renderer.render(
                RenderRequest(job_id=1, scene="../x.blend", frame_start=1, frame_end=1),
                lambda p: None,
            )

        assert not marker.exists()

    def test_a_job_without_a_scene_is_an_error(self, tmp_path: Path) -> None:
        script = _fake_blender(tmp_path, "pass\n")

        with pytest.raises(RenderError, match="scene"):
            self._renderer(tmp_path, script).render(
                RenderRequest(job_id=1, scene=None, frame_start=1, frame_end=1), lambda p: None
            )

    def test_the_child_does_not_inherit_the_worker_secrets(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("QUEUEWATCH_API_TOKENS", "admin=super-secret-token")
        monkeypatch.setenv("CELERY_BROKER_URL", "redis://:pw@redis/0")
        marker = tmp_path / "env.txt"
        script = _fake_blender(
            tmp_path,
            f"""
            import os, pathlib, sys
            pathlib.Path({str(marker)!r}).write_text(",".join(sorted(os.environ)))
            args = sys.argv
            out = pathlib.Path(args[args.index("-o") + 1])
            out.parent.mkdir(parents=True, exist_ok=True)
            (out.parent / "frame_0001.png").write_bytes(b"x")
            """,
        )

        self._renderer(tmp_path, script).render(self._request(tmp_path), lambda p: None)

        names = marker.read_text().split(",")
        assert "QUEUEWATCH_API_TOKENS" not in names
        assert "CELERY_BROKER_URL" not in names
        assert "PATH" in names


class TestSimulatedRenderer:
    def test_it_succeeds_when_the_failure_rate_is_zero(self) -> None:
        result = SimulatedRenderer(failure_rate=0.0, sleep=lambda s: None).render(
            RenderRequest(job_id=1, scene=None, frame_start=1, frame_end=1), lambda p: None
        )

        assert result.frames == 0
        assert result.output_dir is None

    def test_it_raises_a_render_error_when_the_failure_rate_is_one(self) -> None:
        renderer = SimulatedRenderer(failure_rate=1.0, sleep=lambda s: None)

        with pytest.raises(RenderError, match="Simulated render failure"):
            renderer.render(
                RenderRequest(job_id=1, scene=None, frame_start=1, frame_end=1), lambda p: None
            )

    def test_the_simulated_duration_is_within_the_configured_range(self) -> None:
        slept: list[float] = []
        renderer = SimulatedRenderer(
            failure_rate=0.0, sleep=slept.append, min_seconds=2.0, max_seconds=15.0
        )

        for _ in range(50):
            renderer.render(
                RenderRequest(job_id=1, scene=None, frame_start=1, frame_end=1), lambda p: None
            )

        assert all(2.0 <= s <= 15.0 for s in slept)

    def test_it_reports_completion(self) -> None:
        seen: list[int] = []

        SimulatedRenderer(failure_rate=0.0, sleep=lambda s: None).render(
            RenderRequest(job_id=1, scene=None, frame_start=1, frame_end=1), seen.append
        )

        assert seen[-1] == 100
        assert os.name  # keep the import used
