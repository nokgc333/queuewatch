"""ジョブ登録・一覧・詳細・削除エンドポイント（仕様書§5.2, §5.3参照）。"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from kombu.exceptions import KombuError
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.auth import requires_admin, requires_editor, requires_viewer
from app.config import settings
from app.database import get_db
from app.domain.priority_queue import resolve_queue_name
from app.models import Job
from app.renderers import SceneNotAllowedError, resolve_scene
from app.schemas import JobCreate, JobDetailOut, JobOut
from app.tasks import process_render_job

logger = logging.getLogger(__name__)

router = APIRouter()

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
    status: str | None = None,
    priority: str | None = None,
    db: Session = Depends(get_db),
) -> list[Job]:
    """ジョブ一覧を取得する（`status`/`priority`クエリでフィルタ、仕様書§5.5）。"""
    query = db.query(Job)
    if status is not None:
        query = query.filter(Job.status == status)
    if priority is not None:
        query = query.filter(Job.priority == priority)
    return query.order_by(Job.created_at.desc()).all()


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
