"""process_render_jobタスク本体（仕様書§5.3, §10, ADR-0002, ADR-0007参照）。

レンダリングは `Renderer`(app/renderers.py)に任せる。既定は疑似レンダー(ADR-0002)で、
`RENDERER=blender` にすると実 Blender を動かす(ADR-0007)。再試行・バックオフ・デッドレター・
冪等性の骨格は、どちらでも同じ。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Job, RetryLog
from app.renderers import (
    BlenderRenderer,
    Renderer,
    RenderError,
    RenderRequest,
    SimulatedRenderer,
)
from app.worker import celery_app

logger = get_task_logger(__name__)

# 疑似失敗率（要件定義書FR-002、環境変数FAILURE_RATEで調整可能）。
# モジュールレベル変数として切り出すことで、テストからmonkeypatchで上書きできる
# (仕様書§12.2 test_tasks.py参照)。
FAILURE_RATE = settings.FAILURE_RATE

# 疑似レンダリングの処理時間レンジ（正規分布のクリップ範囲、秒）
MIN_DURATION_SECONDS = 2.0
MAX_DURATION_SECONDS = 15.0
DURATION_MEAN_SECONDS = 7.0
DURATION_STDDEV_SECONDS = 3.0


def get_renderer() -> Renderer:
    """設定に応じたレンダラーを作る。疑似の定数は、テストが差し替えられるよう、呼び出し時に読む。"""
    if settings.RENDERER == "blender":
        return BlenderRenderer(
            settings.BLENDER_PATH,
            Path(settings.RENDER_SCENE_ROOT),
            Path(settings.RENDER_OUTPUT_ROOT),
            settings.RENDER_TIMEOUT_SECONDS,
        )
    return SimulatedRenderer(
        failure_rate=FAILURE_RATE,
        min_seconds=MIN_DURATION_SECONDS,
        max_seconds=MAX_DURATION_SECONDS,
        mean_seconds=DURATION_MEAN_SECONDS,
        stddev_seconds=DURATION_STDDEV_SECONDS,
    )


@celery_app.task(
    bind=True,
    autoretry_for=(RenderError,),
    retry_backoff=True,  # 指数バックオフ（1s, 2s, 4s...）
    retry_backoff_max=60,  # バックオフ間隔の上限
    retry_jitter=True,  # サンダリングハード対策
    max_retries=3,
)
def process_render_job(self, job_id: int) -> None:  # type: ignore[no-untyped-def]
    """ジョブを疑似的に処理するCeleryタスク。

    実際のレンダリングは行わず、処理時間を正規分布でシミュレートしている
    （ADR-0002、疑似レンダーファーム方針）。

    冪等性設計（仕様書§10.5）: 既にstatus="success"の場合は
    処理をスキップして即座にreturnする。acks_late=Trueにより
    ワーカークラッシュ時の再配信でタスクが複数回実行されうるため、
    このガードが結果の一貫性を保証する。
    """
    db: Session = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            logger.warning("job %s not found, skipping", job_id)
            return
        if job.status == "success":
            logger.info("job %s already succeeded, skipping duplicate execution", job_id)
            return

        job.status = "running"
        job.started_at = job.started_at or datetime.now(timezone.utc)
        job.celery_task_id = self.request.id
        db.commit()

        def save_progress(value: int) -> None:
            job.progress = value
            db.commit()

        result = get_renderer().render(
            RenderRequest(
                job_id=job.id,
                scene=job.scene,
                frame_start=job.frame_start,
                frame_end=job.frame_end,
            ),
            save_progress,
        )
        job.progress = 100
        job.output_dir = result.output_dir
        job.status = "success"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    except RenderError as exc:
        if job is None:
            raise
        job.retry_count += 1
        job.error_message = str(exc)
        attempt = RetryLog(
            job_id=job_id,
            attempt_number=job.retry_count,
            status="failed",
            error_message=str(exc),
        )
        db.add(attempt)

        if job.retry_count >= job.max_retries:
            job.status = "dead"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            logger.error("job %s exceeded max_retries, moved to dead", job_id)
            return  # リトライを打ち切る（DLQ相当、要件定義書FR-005）

        job.status = "retrying"
        db.commit()
        raise  # Celeryのautoretry_forに委ねて指数バックオフで再スケジュール
    finally:
        db.close()
