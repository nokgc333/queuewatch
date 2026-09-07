"""環境変数管理（仕様書§11.5 env-vars参照）。

Pydantic Settingsによる型検証を行い、起動時に不正な値を早期検知する
（PipeBoardと同一方針）。
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    DATABASE_URL: str = "sqlite:///./queuewatch.db"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False
    FAILURE_RATE: float = 0.10
    MAX_RETRIES: int = 3
    CORS_ALLOW_ORIGINS: str = "*"


settings = Settings()
