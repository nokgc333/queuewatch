"""ワーカー稼働状況エンドポイント（仕様書§5.2 FR-003参照）。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import requires_viewer
from app.database import get_db
from app.domain.stats import calculate_utilization
from app.models import WorkerStat
from app.schemas import WorkerStatusOut

router = APIRouter()


@router.get("/status", response_model=list[WorkerStatusOut], dependencies=[requires_viewer])
def get_worker_status(db: Session = Depends(get_db)) -> list[WorkerStatusOut]:
    """ワーカーごとの直近ウィンドウの稼働率・処理件数を返す（FR-003）。

    `worker_stats`テーブルはworker_name単位で複数ウィンドウの行を持ちうるため、
    worker_name別に最新の行（window_startが最大）を採用する。
    """
    stats = db.query(WorkerStat).order_by(WorkerStat.window_start.desc()).all()

    latest_by_worker: dict[str, WorkerStat] = {}
    for stat in stats:
        if stat.worker_name not in latest_by_worker:
            latest_by_worker[stat.worker_name] = stat

    results: list[WorkerStatusOut] = []
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
            WorkerStatusOut(
                worker_name=stat.worker_name,
                processed_count=stat.processed_count,
                failed_count=stat.failed_count,
                utilization=round(utilization, 2),
            )
        )
    return results
