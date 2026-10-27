"""docs/api.md(実際の API から生成する API 一覧)のテスト。"""

from __future__ import annotations

from pathlib import Path

from app.export_api_doc import api_markdown, main

COMMITTED = Path(__file__).resolve().parents[2] / "docs" / "api.md"


def test_the_committed_document_matches_the_running_api() -> None:
    assert (
        COMMITTED.read_text(encoding="utf-8") == api_markdown()
    ), "run: python -m app.export_api_doc ../docs/api.md"


def test_every_route_is_listed_with_the_role_it_needs() -> None:
    text = api_markdown()

    for line in (
        "| GET | `/jobs` | viewer |",
        "| POST | `/jobs` | editor |",
        "| DELETE | `/jobs/{job_id}` | admin |",
        "| POST | `/jobs/{job_id}/{action}` | editor |",
        "| GET | `/workers/status` | viewer |",
        "| GET | `/stats/errors` | viewer |",
        "| GET | `/healthz` | なし |",
        "| GET | `/metrics` | viewer |",
    ):
        assert line in text


def test_the_export_writes_the_file_and_checks_its_usage(tmp_path: Path) -> None:
    out = tmp_path / "api.md"

    assert main(["x", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == api_markdown()
    assert main(["x"]) == 2
