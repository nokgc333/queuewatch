"""backend/tests/test_seed.py（デモデータ投入スクリプトの検証）。"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Job, RetryLog, WorkerStat


def test_seed_inserts_expected_demo_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    import app.seed as seed_module

    monkeypatch.setattr(seed_module, "engine", engine)
    monkeypatch.setattr(seed_module, "SessionLocal", factory)

    seed_module.seed()

    db = factory()
    try:
        assert db.query(Job).count() == 5
        assert db.query(RetryLog).count() == 3
        assert db.query(WorkerStat).count() == 1
    finally:
        db.close()
