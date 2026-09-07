"""Celeryアプリ定義・タスク登録（仕様書§5.3, §10.3, §10.6参照）。"""

from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "queuewatch",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],  # SEC-002: pickleシリアライザを許可しない
    result_serializer="json",
    task_acks_late=True,  # at-least-once配信、§10.5冪等性設計と対
    worker_prefetch_multiplier=1,
    task_default_priority=5,
    task_time_limit=30,  # ハードタイムアウト: 30秒でSIGKILL
    task_soft_time_limit=25,  # ソフトタイムアウト: 25秒でSoftTimeLimitExceeded例外
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_ALWAYS_EAGER,
)

celery_app.autodiscover_tasks(["app"])
