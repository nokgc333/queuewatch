"""Pydanticスキーマ（仕様書§4.2, §5参照）。"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    priority: str = Field(default="normal", pattern="^(high|normal|low)$")


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    priority: str
    status: str
    celery_task_id: str | None
    retry_count: int
    max_retries: int
    error_message: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None


class RetryLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    attempt_number: int
    status: str
    error_message: str | None
    attempted_at: datetime.datetime


class JobDetailOut(JobOut):
    retry_logs: list[RetryLogOut] = Field(default_factory=list)


class JobListParams(BaseModel):
    """将来のページネーション拡張に備えた型定義のみ先行して用意する（仕様書§4.9）。

    v1では実装スコープ外であり、limit/offsetはAPIハンドラでは使用しない。
    """

    status: str | None = None
    priority: str | None = None
    limit: int | None = None
    offset: int | None = None


class WorkerStatusOut(BaseModel):
    """ワーカー稼働状況(FR-003)。DBのworker_statsを集計してこの形に整形する。"""

    worker_name: str
    processed_count: int
    failed_count: int
    utilization: float


class UtilizationStatOut(BaseModel):
    worker_name: str
    utilization: float


class DurationBinOut(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class ErrorBreakdownItemOut(BaseModel):
    error_message: str
    count: int
