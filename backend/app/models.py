"""SQLAlchemyモデル（仕様書§4.1 ER図・§4.2 データ辞書参照）。"""

from __future__ import annotations

import datetime

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_priority_status", "priority", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(10), default="normal")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=3)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scene: Mapped[str | None] = mapped_column(String(255), nullable=True)
    frame_start: Mapped[int] = mapped_column(default=1)
    frame_end: Mapped[int] = mapped_column(default=1)
    progress: Mapped[int] = mapped_column(default=0)
    output_dir: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)
    started_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    retry_logs: Mapped[list["RetryLog"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class RetryLog(Base):
    __tablename__ = "retry_logs"
    __table_args__ = (Index("idx_retry_logs_job_id", "job_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    attempt_number: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(String(20))
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempted_at: Mapped[datetime.datetime] = mapped_column(default=_utcnow)

    job: Mapped["Job"] = relationship(back_populates="retry_logs")


class WorkerStat(Base):
    __tablename__ = "worker_stats"
    __table_args__ = (Index("idx_worker_stats_window", "window_start", "window_end"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    worker_name: Mapped[str] = mapped_column(String(100))
    processed_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    total_busy_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    window_start: Mapped[datetime.datetime] = mapped_column()
    window_end: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
