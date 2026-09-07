"""backend/tests/test_tasks.py（TC-004, TC-005, TC-008〜010, TC-018相当、
CELERY_TASK_ALWAYS_EAGER=trueでの同期実行テスト、仕様書§12.2, §12.5）。
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models import Job, RetryLog
from app.tasks import process_render_job


def test_process_render_job_succeeds_and_records_timestamps(
    db_session: Session,
) -> None:
    """FAILURE_RATE=0(既定パッチ)のとき、ジョブはsuccessに到達する。"""
    job = Job(name="TEST_JOB", priority="normal", status="pending")
    db_session.add(job)
    db_session.commit()

    process_render_job.apply(args=[job.id]).get(propagate=True)

    db_session.refresh(job)
    assert job.status == "success"
    assert job.started_at is not None
    assert job.finished_at is not None
    assert job.celery_task_id is not None


def test_process_render_job_retries_on_failure_and_records_retry_log(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-008相当: 失敗タスクがretry_logsに記録されretry_countが増加する。

    eagerモードの`apply()`は実際のワーカー再配信をシミュレートしない
    (1回の呼び出し = 1回の試行のみ実行し、Celeryの`autoretry_for`は
    リトライ予定を示す`Retry`例外を送出するだけで自動的にはループしない、
    仕様書§12.5の制約と対応)。そのため、1回のapply()呼び出し後には
    retry_count=1・status="retrying"となることを検証する。
    """
    monkeypatch.setattr("app.tasks.FAILURE_RATE", 1.0)  # 常に失敗させる
    job = Job(name="TEST_JOB_FAIL", priority="normal", status="pending", max_retries=3)
    db_session.add(job)
    db_session.commit()

    with pytest.raises(Exception):
        process_render_job.apply(args=[job.id]).get(propagate=True)

    db_session.refresh(job)
    assert job.retry_count == 1
    assert job.status == "retrying"
    logs = db_session.query(RetryLog).filter(RetryLog.job_id == job.id).all()
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert logs[0].attempt_number == 1


def test_process_render_job_moves_to_dead_after_max_retries(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-009/TC-010相当: max_retries到達でstatus="dead"となりリトライが打ち切られる（FR-005）。

    実際のワーカー環境では、Celeryが失敗のたびにタスクを再配信し
    process_render_jobが複数回呼び出される。eagerモードにはこの自動再配信が
    ないため、apply()をmax_retries回だけ手動で繰り返し呼び出し、実運用での
    複数回配信を模擬する。
    """
    monkeypatch.setattr("app.tasks.FAILURE_RATE", 1.0)
    job = Job(name="TEST_JOB_DEAD", priority="normal", status="pending", max_retries=3)
    db_session.add(job)
    db_session.commit()

    for _ in range(job.max_retries):
        try:
            process_render_job.apply(args=[job.id]).get(propagate=True)
        except Exception:
            pass

    db_session.refresh(job)
    assert job.status == "dead"
    assert job.retry_count == job.max_retries
    assert job.finished_at is not None
    assert job.error_message is not None


def test_process_render_job_is_idempotent_for_already_succeeded_job(
    db_session: Session,
) -> None:
    """仕様書§10.5: status="success"のジョブは再実行時にスキップされる（冪等性ガード）。"""
    job = Job(name="TEST_JOB_DONE", priority="normal", status="success")
    db_session.add(job)
    db_session.commit()
    original_updated_at = job.updated_at

    process_render_job.apply(args=[job.id]).get(propagate=True)

    db_session.refresh(job)
    assert job.status == "success"
    # 二重処理されていない(started_atが設定されない = 実処理ブロックを通過していない)
    assert job.started_at is None
    assert job.updated_at == original_updated_at


def test_process_render_job_skips_missing_job(db_session: Session) -> None:
    """存在しないjob_idを渡された場合は警告ログのみでエラーにしない。"""
    process_render_job.apply(args=[999999]).get(propagate=True)  # 例外を送出しないことを確認


def test_process_render_job_uses_json_serializer() -> None:
    """SEC-002: pickleシリアライザを許可しない設定になっていることを検証する（仕様書§9.7）。"""
    from app.worker import celery_app

    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
