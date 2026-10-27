"""README・ADR・運用手順書・画像が、実態と合っていることのテスト。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_every_adr_is_listed_in_the_readme_and_there_are_at_least_nine() -> None:
    adrs = sorted((ROOT / "docs" / "adr").glob("*.md"))

    assert len(adrs) >= 9
    for adr in adrs:
        assert f"docs/adr/{adr.name}" in README, adr.name


def test_the_readme_images_exist() -> None:
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", README)

    assert len(images) >= 4
    for image in images:
        assert (ROOT / image).is_file(), image


def test_relative_links_in_the_readme_point_to_existing_files() -> None:
    for link in re.findall(r"\]\(((?:docs|\.env)[^)#]*|CHANGELOG\.md|LICENSE)\)", README):
        assert (ROOT / link).exists(), link


def test_the_readme_has_an_english_summary_and_an_architecture_diagram() -> None:
    assert "English summary" in README
    assert "```mermaid" in README


def test_the_simulated_only_claim_was_removed_because_a_real_renderer_exists() -> None:
    assert "実際のHoudini/Nukeレンダリングは一切行いません" not in README
    assert "RENDERER=blender" in README


def test_the_operations_manual_covers_the_main_situations() -> None:
    text = (ROOT / "docs/operations.md").read_text(encoding="utf-8")

    for heading in ("## 起動", "## 障害対応", "## キューが滞留したとき", "## データ"):
        assert heading in text
    assert "python -m app.migrate stamp 0001" in text
    assert "s.backup(d)" in text
