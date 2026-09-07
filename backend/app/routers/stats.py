"""統計エンドポイント（仕様書§5.2, §6.4, §8.3参照）。"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.stats import calculate_duration_histogram, calculate_utilization
from app.models import Job, RetryLog, WorkerStat
from app.schemas import DurationBinOut, ErrorBreakdownItemOut, UtilizationStatOut

router = APIRouter()


@router.get("/utilization", response_model=list[UtilizationStatOut])
def get_utilization_stats(db: Session = Depends(get_db)) -> list[UtilizationStatOut]:
    """ワーカー稼働率統計（FR-008）。worker_name単位の最新ウィンドウを集計する。"""
    stats = db.query(WorkerStat).order_by(WorkerStat.window_start.desc()).all()

    latest_by_worker: dict[str, WorkerStat] = {}
    for stat in stats:
        latest_by_worker.setdefault(stat.worker_name, stat)

    results: list[UtilizationStatOut] = []
    for stat in latest_by_worker.values():
        window_end = stat.window_end or datetime.now(timezone.utc)
        window_start = stat.window_start
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=timezone.utc)
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=timezone.utc)
        window_seconds = (window_end - window_start).total_seconds()
        utilization = calculate_utilization(stat.total_busy_seconds, window_seconds)
        results.append(
            UtilizationStatOut(worker_name=stat.worker_name, utilization=round(utilization, 2))
        )
    return results


@router.get("/duration", response_model=list[DurationBinOut])
def get_duration_stats(db: Session = Depends(get_db)) -> list[DurationBinOut]:
    """処理時間分布統計（FR-008）。jobs.started_at〜finished_atからヒストグラムを生成する。"""
    jobs = db.query(Job).filter(Job.started_at.is_not(None), Job.finished_at.is_not(None)).all()
    durations = [
        (job.finished_at - job.started_at).total_seconds() for job in jobs  # type: ignore[operator]
    ]
    bins = calculate_duration_histogram(durations)
    return [
        DurationBinOut(bin_start=round(start, 2), bin_end=round(end, 2), count=count)
        for start, end, count in bins
    ]


@router.get("/errors", response_model=list[ErrorBreakdownItemOut])
def get_error_stats(db: Session = Depends(get_db)) -> list[ErrorBreakdownItemOut]:
    """エラー種別集計（FR-005）。retry_logs.error_messageを分類集計する。"""
    logs = (
        db.query(RetryLog)
        .filter(RetryLog.status == "failed", RetryLog.error_message.is_not(None))
        .all()
    )
    counts = Counter(str(log.error_message) for log in logs)
    return [
        ErrorBreakdownItemOut(error_message=message, count=count)
        for message, count in counts.most_common()
    ]
