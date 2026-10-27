"""Alembic のマイグレーションのテスト(空の DB から最新まで再現でき、モデルと食い違わない)。"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app import models  # noqa: F401
from app.database import Base
from app.migrate import alembic_config, main, stamp, upgrade_to_head

TABLES = {"jobs", "retry_logs", "worker_stats"}


def _url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'migrated.db'}"


def test_upgrading_an_empty_database_creates_every_table(tmp_path: Path) -> None:
    url = _url(tmp_path)

    upgrade_to_head(url)

    assert TABLES <= set(inspect(create_engine(url)).get_table_names())


def test_the_migrated_schema_matches_the_models(tmp_path: Path) -> None:
    url = _url(tmp_path)
    upgrade_to_head(url)

    with create_engine(url).connect() as connection:
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert differences == []


def test_the_job_columns_added_for_real_rendering_exist(tmp_path: Path) -> None:
    url = _url(tmp_path)
    upgrade_to_head(url)

    columns = {c["name"] for c in inspect(create_engine(url)).get_columns("jobs")}

    assert {"scene", "frame_start", "frame_end", "progress", "output_dir"} <= columns


def test_upgrading_twice_is_harmless(tmp_path: Path) -> None:
    url = _url(tmp_path)

    upgrade_to_head(url)
    upgrade_to_head(url)

    assert TABLES <= set(inspect(create_engine(url)).get_table_names())


def test_downgrading_to_base_removes_the_tables(tmp_path: Path) -> None:
    url = _url(tmp_path)
    upgrade_to_head(url)

    command.downgrade(alembic_config(url), "base")

    assert not (TABLES & set(inspect(create_engine(url)).get_table_names()))


def test_a_database_created_by_create_all_can_be_stamped_and_keeps_its_data(
    tmp_path: Path,
) -> None:
    url = _url(tmp_path)
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO jobs (name, priority, status, retry_count, max_retries, "
                "frame_start, frame_end, progress, created_at, updated_at) VALUES "
                "('JOB_A', 'high', 'success', 0, 3, 1, 1, 100, '2026-01-01', '2026-01-01')"
            )
        )

    stamp("0001", url)
    upgrade_to_head(url)

    with engine.connect() as connection:
        names = [r[0] for r in connection.execute(text("SELECT name FROM jobs"))]
    assert names == ["JOB_A"]


def test_the_command_line_is_checked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app import migrate

    monkeypatch.setattr(migrate, "upgrade_to_head", lambda *a, **k: None)
    monkeypatch.setattr(migrate, "stamp", lambda *a, **k: None)

    assert main(["m"]) == 0
    assert main(["m", "stamp", "0001"]) == 0
    assert main(["m", "bogus"]) == 2
