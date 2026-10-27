"""ジョブ登録・一覧・詳細・削除エンドポイント（仕様書§5.2, §5.3参照）。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from kombu.exceptions import KombuError
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.auth import requires_admin, requires_editor, requires_viewer
from app.config import settings
from app.database import get_db
from app.domain.job_actions import ACTIONS, next_status
from app.domain.priority_queue import resolve_queue_name
from app.models import Job
from app.renderers import SceneNotAllowedError, resolve_scene
from app.schemas import JobCreate, JobDetailOut, JobOut
from app.tasks import process_render_job

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_PAGE_SIZE = 500

# Redis/Celeryブローカー接続不可時に実際に送出されうる例外群。
# redis-pyはConnectionError/RedisError系、kombu(Celeryのメッセージング抽象化層)は
# KombuError系、さらにceleryのbackends.asynchronousは再接続上限到達時に
# 素のRuntimeErrorを送出する（実機検証で確認、仕様書§2.7 ERR-BROKER-UNAVAILABLE）。
BROKER_UNAVAILABLE_EXCEPTIONS = (ConnectionError, RedisError, KombuError, OSError, RuntimeError)


def _check_scene(payload: JobCreate) -> None:
    """実レンダラーのときは、投入の時点で、シーンが許可されていることを確かめる(422)。"""
    if settings.RENDERER != "blender":
        return
    if payload.scene is None:
        raise HTTPException(status_code=422, detail="scene is required when RENDERER=blender")
    try:
        resolve_scene(Path(settings.RENDER_SCENE_ROOT), payload.scene)
    except SceneNotAllowedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[JobOut], dependencies=[requires_viewer])
def list_jobs(
    response: Response,
    q: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, max_length=20),
    priority: str | None = Query(default=None, max_length=10),
    limit: int = Query(default=MAX_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Job]:
    """ジョブ一覧(`q` は名前の部分一致、`status` / `priority` で絞り込み、`limit` / `offset` でページング)。

    条件に合う総件数は、ヘッダ `X-Total-Count` で返す。
    """
    query = db.query(Job)
    if q:
        query = query.filter(Job.name.icontains(q, autoescape=True))
    if status is not None:
        query = query.filter(Job.status == status)
    if priority is not None:
        query = query.filter(Job.priority == priority)
    response.headers["X-Total-Count"] = str(query.count())
    return query.order_by(Job.created_at.desc(), Job.id.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=JobOut, status_code=201, dependencies=[requires_editor])
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> Job:
    """ジョブを登録し、優先度に応じたキューへpublishする（FR-001/006）。

    Redis接続不可時はpublishに失敗し503を返す（仕様書§2.7, §5.4 ERR-BROKER-UNAVAILABLE）。
    DB上には`status="pending"`のまま孤立したレコードが残る可能性があるが、
    これはv1が許容するリスクとして仕様書に明記済み。
    """
    _check_scene(payload)
    job = Job(
        name=payload.name,
        priority=payload.priority,
        status="pending",
        scene=payload.scene,
        frame_start=payload.frame_start,
        frame_end=payload.frame_end,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    queue_name = resolve_queue_name(job.priority)
    try:
        process_render_job.apply_async(args=[job.id], queue=queue_name)
    except BROKER_UNAVAILABLE_EXCEPTIONS as exc:
        logger.error("failed to publish job %s to broker: %s", job.id, exc)
        raise HTTPException(status_code=503, detail="Queue service unavailable") from exc

    db.refresh(job)
    return job


@router.get("/{job_id}", response_model=JobDetailOut, dependencies=[requires_viewer])
def get_job(job_id: int, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.delete("/{job_id}", status_code=204, dependencies=[requires_admin])
def delete_job(job_id: int, db: Session = Depends(get_db)) -> None:
    """ジョブを削除する（retry_logsもカスケード削除、仕様書§4.4）。"""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    db.delete(job)
    db.commit()


def _publish(job: Job) -> None:
    queue_name = resolve_queue_name(job.priority)
    try:
        process_render_job.apply_async(args=[job.id], queue=queue_name)
    except BROKER_UNAVAILABLE_EXCEPTIONS as exc:
        logger.error("failed to publish job %s to broker: %s", job.id, exc)
        raise HTTPException(status_code=503, detail="Queue service unavailable") from exc


@router.post("/{job_id}/{action}", response_model=JobOut, dependencies=[requires_editor])
def control_job(job_id: int, action: str, db: Session = Depends(get_db)) -> Job:
    """ジョブを、キャンセル・一時停止・再開・再投入する(cancel / pause / resume / requeue)。

    キューに残ったメッセージは、ワーカーが状態を見て読み飛ばす(cancelled / paused はスキップ)。
    """
    if action not in ACTIONS:
        raise HTTPException(status_code=404, detail=f"Unknown action '{action}'")
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    target = next_status(action, job.status)
    if target is None:
        raise HTTPException(status_code=409, detail=f"Cannot {action} a job that is {job.status}")
    previous = job.status
    job.status = target
    if target == "cancelled":
        job.finished_at = datetime.now(timezone.utc)
    if action == "requeue":
        job.retry_count = 0
        job.error_message = None
        job.progress = 0
        job.finished_at = None
        job.output_dir = None
    db.commit()
    logger.info(
        "job action",
        extra={"job_id": job.id, "action": action, "from": previous, "to": target},
    )
    if target == "pending":
        _publish(job)
    db.refresh(job)
    return job
