"""process_render_jobタスク本体（仕様書§5.3, §10, ADR-0002参照）。

**重要な設計上の正直さ（ADR-0002）**: このタスクは実際のレンダリングを一切行わない。
Houdini/Nuke等の実レンダリングエンジンとの統合は本プロジェクトのスコープ外であり、
`time.sleep()`による処理時間のシミュレーションと、確率的な疑似失敗
(`FAILURE_RATE`)によって、分散タスクキューのキューイング・ワーカー処理・
リトライ・デッドレターキューという「本質的に検証したい設計」を再現している。
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone

from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Job, RetryLog
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


@celery_app.task(
    bind=True,
    autoretry_for=(RuntimeError,),
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

        # 疑似レンダリング処理: 正規分布で2〜15秒の処理時間をシミュレート
        duration = max(
            MIN_DURATION_SECONDS,
            min(MAX_DURATION_SECONDS, random.gauss(DURATION_MEAN_SECONDS, DURATION_STDDEV_SECONDS)),
        )
        time.sleep(duration)

        if random.random() < FAILURE_RATE:
            raise RuntimeError("Simulated render failure (license server timeout)")

        job.status = "success"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    except RuntimeError as exc:
        # job is always bound here: RuntimeError is only raised after the
        # `job is None` early-return above has already passed.
        assert job is not None
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
