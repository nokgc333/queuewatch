"""houdini_submit_job.py の単体テスト（仕様書§16.E、FR-007対応、TC-013〜015相当）。

Houdini実機環境をCIに組み込むことは現実的でないため、HTTP呼び出しロジックのみを
hou非依存の関数として切り出し、requestsのレスポンスをモックして検証する
（PipeBoardのhoudini_status_update.pyと同一設計思想）。
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from houdini_submit_job import build_jobs_url, submit_job  # noqa: E402


def test_build_jobs_url() -> None:
    assert build_jobs_url("http://localhost:8000") == "http://localhost:8000/jobs"


def test_build_jobs_url_strips_trailing_slash() -> None:
    assert build_jobs_url("http://localhost:8000/") == "http://localhost:8000/jobs"


def test_submit_job_posts_expected_payload() -> None:
    session = MagicMock()
    session.post.return_value.status_code = 201
    session.post.return_value.json.return_value = {
        "id": 12,
        "name": "SHOT010_render",
        "status": "pending",
    }

    result = submit_job(
        "http://localhost:8000", "SHOT010_render", "high", session=session
    )

    session.post.assert_called_once_with(
        "http://localhost:8000/jobs",
        json={"name": "SHOT010_render", "priority": "high"},
        timeout=5,
    )
    assert result == {"id": 12, "name": "SHOT010_render", "status": "pending"}


def test_submit_job_defaults_priority_to_normal() -> None:
    session = MagicMock()
    session.post.return_value.status_code = 201
    session.post.return_value.json.return_value = {"id": 1, "status": "pending"}

    submit_job("http://localhost:8000", "SHOT020_render", session=session)

    session.post.assert_called_once_with(
        "http://localhost:8000/jobs",
        json={"name": "SHOT020_render", "priority": "normal"},
        timeout=5,
    )


def test_submit_job_rejects_invalid_priority() -> None:
    session = MagicMock()

    with pytest.raises(ValueError, match="priority"):
        submit_job("http://localhost:8000", "SHOT030_render", "urgent", session=session)

    session.post.assert_not_called()


def test_submit_job_raises_on_http_error() -> None:
    session = MagicMock()
    session.post.return_value.status_code = 422
    session.post.return_value.raise_for_status.side_effect = Exception(
        "422 Unprocessable Entity"
    )

    with pytest.raises(Exception, match="422"):
        submit_job("http://localhost:8000", "", "high", session=session)


def test_submit_job_uses_requests_module_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sessionを渡さない場合はrequestsモジュールがそのまま使われることを確認する。"""
    import houdini_submit_job

    fake_requests = MagicMock()
    fake_requests.post.return_value.status_code = 201
    fake_requests.post.return_value.json.return_value = {"id": 5, "status": "pending"}
    monkeypatch.setattr(houdini_submit_job, "requests", fake_requests)

    result = submit_job("http://localhost:8000", "SHOT040_render", "low")

    fake_requests.post.assert_called_once()
    assert result == {"id": 5, "status": "pending"}
