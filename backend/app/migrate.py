"""マイグレーションを最新まで適用する(起動時・seed・テストから使う)。"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.database import DATABASE_URL

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def upgrade_to_head(database_url: str = DATABASE_URL) -> None:
    command.upgrade(alembic_config(database_url), "head")


def stamp(revision: str, database_url: str = DATABASE_URL) -> None:
    """マイグレーション導入前に作られたデータベースを、実行せずに「その版まで適用済み」にする。"""
    command.stamp(alembic_config(database_url), revision)


def main(argv: list[str]) -> int:
    if len(argv) == 1:
        upgrade_to_head()
        return 0
    if len(argv) == 3 and argv[1] == "stamp":
        stamp(argv[2])
        return 0
    print("usage: python -m app.migrate [stamp <revision>]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
