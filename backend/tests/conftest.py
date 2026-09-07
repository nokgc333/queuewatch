"""pytest共通フィクスチャ。テストごとに独立したin-memory SQLiteを使う
（PipeBoardのdb_session_factoryパターンを踏襲、仕様書§3.5）。
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def eager_celery(monkeypatch: pytest.MonkeyPatch) -> None:
    """全テストでCeleryタスクをeagerモード(同期実行)にする（仕様書§3.5, §12.5）。"""
    from app.worker import celery_app

    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@pytest.fixture(autouse=True)
def fast_render_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    """テスト実行中は疑似レンダリング処理のtime.sleep()をほぼゼロ秒に短縮する。

    本番コードのMIN/MAX_DURATION_SECONDS(2〜15秒、仕様書§5.3)自体は変更せず、
    テストからのみ差し替えることでCIの実行時間を現実的に保つ（数百テストが
    毎回2〜15秒待つとテストスイートが非現実的な時間になるため）。
    """
    import app.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "MIN_DURATION_SECONDS", 0.0)
    monkeypatch.setattr(tasks_module, "MAX_DURATION_SECONDS", 0.01)
    monkeypatch.setattr(tasks_module, "DURATION_MEAN_SECONDS", 0.0)
    monkeypatch.setattr(tasks_module, "DURATION_STDDEV_SECONDS", 0.0)


@pytest.fixture(autouse=True)
def deterministic_failure_rate(monkeypatch: pytest.MonkeyPatch) -> None:
    """既定ではFAILURE_RATEを0にし、疑似失敗による非決定的なテスト失敗を防ぐ。

    リトライ・DLQ挙動を検証するテスト(test_tasks.py)は個別に
    ``monkeypatch.setattr("app.tasks.FAILURE_RATE", 1.0)`` で上書きする
    (仕様書§12.2の例と同じパターン)。
    """
    import app.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "FAILURE_RATE", 0.0)


@pytest.fixture()
def db_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[sessionmaker[Session], None, None]:
    """テスト専用のin-memory SQLiteエンジンを作り、Celeryタスク内部の
    ``SessionLocal``（app.tasks.SessionLocal）も同じエンジンに差し替える。

    eagerモードではAPI呼び出しの中でCeleryタスクが同期的に実行されるため、
    タスク内部が実DBファイル（queuewatch.db）を見てしまうとテストのin-memory DB
    と食い違いジョブが見つからなくなる。この差し替えでAPI層とタスク層が
    同一のDBを参照するようにする。
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    import app.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "SessionLocal", factory)

    yield factory


@pytest.fixture()
def db_session(db_session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = db_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(
    db_session_factory: sessionmaker[Session],
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = db_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
