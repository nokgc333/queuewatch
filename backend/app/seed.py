"""デモデータ投入スクリプト（仕様書§1 quick-reference参照）。

`python -m app.seed` で実行する。実際にCeleryへpublishはせず、
DBへの直接INSERTのみでデモ用の様々なステータスのジョブを再現する
（ワーカー・Redisが起動していない状態でもダッシュボードの見た目を確認できるように
する目的）。
"""

from __future__ import annotations

import datetime

from app.database import Base, SessionLocal, engine
from app.models import Job, RetryLog, WorkerStat


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        now = _utcnow()

        pending = Job(name="SHOT010_render", priority="high", status="pending")
        running = Job(
            name="SHOT020_render",
            priority="normal",
            status="running",
            started_at=now - datetime.timedelta(seconds=5),
        )
        success = Job(
            name="SHOT030_render",
            priority="low",
            status="success",
            started_at=now - datetime.timedelta(seconds=30),
            finished_at=now - datetime.timedelta(seconds=20),
        )
        retrying = Job(
            name="SHOT040_render",
            priority="normal",
            status="retrying",
            retry_count=1,
            started_at=now - datetime.timedelta(seconds=15),
        )
        dead = Job(
            name="SHOT050_render",
            priority="high",
            status="dead",
            retry_count=3,
            error_message="Simulated render failure (license server timeout)",
            started_at=now - datetime.timedelta(seconds=60),
            finished_at=now - datetime.timedelta(seconds=40),
        )
        db.add_all([pending, running, success, retrying, dead])
        db.commit()

        db.add_all(
            [
                RetryLog(
                    job_id=dead.id,
                    attempt_number=1,
                    status="failed",
                    error_message="Simulated render failure (license server timeout)",
                ),
                RetryLog(
                    job_id=dead.id,
                    attempt_number=2,
                    status="failed",
                    error_message="Simulated render failure (license server timeout)",
                ),
                RetryLog(
                    job_id=dead.id,
                    attempt_number=3,
                    status="failed",
                    error_message="Simulated render failure (license server timeout)",
                ),
            ]
        )

        db.add(
            WorkerStat(
                worker_name="celery@demo-worker1",
                processed_count=12,
                failed_count=2,
                total_busy_seconds=95.0,
                window_start=now - datetime.timedelta(minutes=5),
                window_end=now,
            )
        )
        db.commit()
        print("Seeded 5 jobs, 3 retry logs, 1 worker_stat row.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
