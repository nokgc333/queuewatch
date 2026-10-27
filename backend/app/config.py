"""環境変数管理（仕様書§11.5 env-vars参照）。

Pydantic Settingsによる型検証を行い、起動時に不正な値を早期検知する
（PipeBoardと同一方針）。
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    DATABASE_URL: str = "sqlite:///./queuewatch.db"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False
    FAILURE_RATE: float = 0.10
    MAX_RETRIES: int = 3
    RENDERER: Literal["simulated", "blender"] = "simulated"
    BLENDER_PATH: str = "blender"
    RENDER_SCENE_ROOT: str = "./scenes"
    RENDER_OUTPUT_ROOT: str = "./renders"
    RENDER_TIMEOUT_SECONDS: float = Field(default=3600.0, gt=0)


settings = Settings()
