"""Celeryアプリ定義・タスク登録（仕様書§5.3, §10.3, §10.6参照）。"""

from __future__ import annotations

from celery import Celery

from app.config import Settings, settings

SIMULATED_HARD_LIMIT_SECONDS = 30
SIMULATED_SOFT_LIMIT_SECONDS = 25
HARD_LIMIT_MARGIN_SECONDS = 120
SOFT_LIMIT_MARGIN_SECONDS = 60


def task_time_limit(config: Settings) -> int:
    """疑似は 30 秒。実レンダーは、レンダラー自身の制限時間より、少し長く待つ。"""
    if config.RENDERER == "blender":
        return int(config.RENDER_TIMEOUT_SECONDS) + HARD_LIMIT_MARGIN_SECONDS
    return SIMULATED_HARD_LIMIT_SECONDS


def task_soft_time_limit(config: Settings) -> int:
    if config.RENDERER == "blender":
        return int(config.RENDER_TIMEOUT_SECONDS) + SOFT_LIMIT_MARGIN_SECONDS
    return SIMULATED_SOFT_LIMIT_SECONDS


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
    task_time_limit=task_time_limit(settings),  # ハードタイムアウトでSIGKILL
    task_soft_time_limit=task_soft_time_limit(settings),  # ソフトタイムアウトで例外
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_ALWAYS_EAGER,
)

celery_app.autodiscover_tasks(["app"])
