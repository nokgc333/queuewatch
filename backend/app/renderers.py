"""レンダラーのポート(ADR-0007)。疑似レンダー(既定)と、実 Blender をコマンドラインで動かすレンダラー。

実レンダラーは、利用者が渡したシーンのパスから外部プロセスを起動するため、次を守る。
- シーンは、設定した許可ルートの内側の `.blend` に限る(`..`・絶対パス・外を指すシンボリックリンクは拒否)
- コマンドは文字列のリストで渡し、シェルを使わない
- 子プロセスには、ワーカーの秘密(トークン・ブローカーの URL)を渡さない環境変数だけを渡す
- 制限時間を超えたら、プロセスを強制終了する
"""

from __future__ import annotations

import os
import random
import re
import shutil
import subprocess  # nosec B404 - 引数のリストで固定のコマンドだけを起動する
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

SCENE_EXTENSION = ".blend"
OUTPUT_PREFIX = "frame_####"
OUTPUT_FORMAT = "PNG"
OUTPUT_GLOB = "frame_*.png"
TAIL_LINES = 5
KEPT_ENVIRONMENT = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "TEMP", "SYSTEMROOT")
FRAME_LINE = re.compile(r"^Fra:(\d+)\b")

ProgressCallback = Callable[[int], None]


class RenderError(RuntimeError):
    """レンダリングの失敗。Celery の自動リトライの対象(RuntimeError)。"""


class SceneNotAllowedError(RenderError):
    """許可されないシーンのパス。"""


@dataclass(frozen=True)
class RenderRequest:
    job_id: int
    scene: str | None
    frame_start: int
    frame_end: int


@dataclass(frozen=True)
class RenderResult:
    output_dir: str | None
    frames: int


class Renderer(Protocol):
    def render(self, request: RenderRequest, on_progress: ProgressCallback) -> RenderResult: ...


def resolve_scene(root: Path, scene: str) -> Path:
    """許可ルートの内側にある `.blend` の実パスを返す。外・不正な名前は SceneNotAllowedError。"""
    if "\x00" in scene:
        raise SceneNotAllowedError("scene path contains a null byte")
    if scene.startswith("-"):
        raise SceneNotAllowedError("scene path must not start with '-'")
    if scene.startswith("~") or Path(scene).is_absolute():
        raise SceneNotAllowedError("scene path must be relative to the render root")
    if not scene.lower().endswith(SCENE_EXTENSION):
        raise SceneNotAllowedError(f"scene must be a {SCENE_EXTENSION} file")
    real_root = root.resolve()
    candidate = (real_root / scene).resolve()
    if real_root != candidate and real_root not in candidate.parents:
        raise SceneNotAllowedError("scene resolves to a path outside the render root")
    if not candidate.is_file():
        raise SceneNotAllowedError(f"scene '{scene}' does not exist")
    return candidate


def build_blender_command(
    executable: str, scene: Path, output_dir: Path, frame_start: int, frame_end: int
) -> list[str]:
    return [
        executable,
        "-b",
        str(scene),
        "-noaudio",
        "-o",
        str(output_dir / OUTPUT_PREFIX),
        "-F",
        OUTPUT_FORMAT,
        "-s",
        str(frame_start),
        "-e",
        str(frame_end),
        "-a",
    ]


def parse_progress(line: str, frame_start: int, frame_end: int) -> int | None:
    """Blender の出力の `Fra:<n>` から、進捗(0〜100 の整数)を返す。該当しない行は None。"""
    match = FRAME_LINE.match(line)
    if match is None:
        return None
    total = frame_end - frame_start + 1
    done = (int(match.group(1)) - frame_start) / total
    return max(0, min(100, int(done * 100)))


def _child_environment() -> dict[str, str]:
    return {name: os.environ[name] for name in KEPT_ENVIRONMENT if name in os.environ}


class SimulatedRenderer:
    """処理時間(正規分布)と、確率的な失敗だけを再現する疑似レンダー(ADR-0002)。"""

    def __init__(
        self,
        failure_rate: float,
        sleep: Callable[[float], None] = time.sleep,
        min_seconds: float = 2.0,
        max_seconds: float = 15.0,
        mean_seconds: float = 7.0,
        stddev_seconds: float = 3.0,
    ) -> None:
        self._failure_rate = failure_rate
        self._sleep = sleep
        self._min = min_seconds
        self._max = max_seconds
        self._mean = mean_seconds
        self._stddev = stddev_seconds

    def render(self, request: RenderRequest, on_progress: ProgressCallback) -> RenderResult:
        sampled = random.gauss(self._mean, self._stddev)  # nosec B311
        self._sleep(max(self._min, min(self._max, sampled)))
        if random.random() < self._failure_rate:  # nosec B311
            raise RenderError("Simulated render failure (license server timeout)")
        on_progress(100)
        return RenderResult(output_dir=None, frames=0)


class BlenderRenderer:
    def __init__(
        self, executable: str, scene_root: Path, output_root: Path, timeout_seconds: float
    ) -> None:
        self._executable = executable
        self._scene_root = scene_root
        self._output_root = output_root
        self._timeout = timeout_seconds

    def render(self, request: RenderRequest, on_progress: ProgressCallback) -> RenderResult:
        if request.scene is None:
            raise RenderError("a scene is required to render with Blender")
        scene = resolve_scene(self._scene_root, request.scene)
        output_dir = self._output_root / f"job-{int(request.job_id)}"
        shutil.rmtree(output_dir, ignore_errors=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        command = build_blender_command(
            self._executable, scene, output_dir, request.frame_start, request.frame_end
        )
        tail = self._run(command, request, on_progress)
        frames = len(list(output_dir.glob(OUTPUT_GLOB)))
        if frames == 0:
            raise RenderError(f"Blender finished but wrote no frames: {tail}")
        return RenderResult(output_dir=str(output_dir), frames=frames)

    def _run(
        self, command: list[str], request: RenderRequest, on_progress: ProgressCallback
    ) -> str:
        try:
            process = subprocess.Popen(  # nosec B603 - シェルなし、検証済みのパスだけ
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=_child_environment(),
            )
        except OSError as exc:
            raise RenderError(f"Blender could not be started: {exc}") from exc

        timed_out = threading.Event()

        def kill() -> None:
            timed_out.set()
            process.kill()

        watchdog = threading.Timer(self._timeout, kill)
        watchdog.start()
        tail: deque[str] = deque(maxlen=TAIL_LINES)
        reported = -1
        try:
            assert process.stdout is not None
            for raw in process.stdout:
                line = raw.rstrip()
                if line:
                    tail.append(line)
                progress = parse_progress(line, request.frame_start, request.frame_end)
                if progress is not None and progress > reported:
                    reported = progress
                    on_progress(progress)
            code = process.wait()
        finally:
            watchdog.cancel()
            process.stdout and process.stdout.close()
        summary = " | ".join(tail)
        if timed_out.is_set():
            raise RenderError(f"render timed out after {self._timeout:g} seconds: {summary}")
        if code != 0:
            raise RenderError(f"Blender failed with exit code {code}: {summary}")
        return summary
