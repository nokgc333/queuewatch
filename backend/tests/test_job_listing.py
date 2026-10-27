"""ジョブ一覧の検索・絞り込み・ページングのテスト。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Job


@pytest.fixture()
def jobs(db_session: Session) -> None:
    rows = [
        ("SHOT010_render", "high", "success"),
        ("SHOT020_render", "normal", "dead"),
        ("shot_hero", "low", "pending"),
        ("SEQ_B_030", "normal", "dead"),
        ("Chair", "high", "pending"),
    ]
    for name, priority, status in rows:
        db_session.add(Job(name=name, priority=priority, status=status))
        db_session.commit()


def _names(response) -> list[str]:  # type: ignore[no-untyped-def]
    return [j["name"] for j in response.json()]


@pytest.mark.usefixtures("jobs")
class TestListing:
    def test_everything_comes_back_newest_first_by_default(self, client: TestClient) -> None:
        assert _names(client.get("/jobs")) == [
            "Chair",
            "SEQ_B_030",
            "shot_hero",
            "SHOT020_render",
            "SHOT010_render",
        ]

    def test_the_total_count_counts_all_matches_not_just_the_page(self, client: TestClient) -> None:
        response = client.get("/jobs?limit=2")

        assert len(response.json()) == 2
        assert response.headers["X-Total-Count"] == "5"

    def test_offset_skips_from_the_start_and_the_last_page_can_be_short(
        self, client: TestClient
    ) -> None:
        assert _names(client.get("/jobs?limit=2&offset=2")) == ["shot_hero", "SHOT020_render"]
        assert _names(client.get("/jobs?limit=2&offset=4")) == ["SHOT010_render"]

    def test_an_offset_past_the_end_is_empty_with_the_real_total(self, client: TestClient) -> None:
        response = client.get("/jobs?offset=99")

        assert response.json() == []
        assert response.headers["X-Total-Count"] == "5"

    def test_search_matches_part_of_the_name_ignoring_case(self, client: TestClient) -> None:
        assert _names(client.get("/jobs?q=shot")) == [
            "shot_hero",
            "SHOT020_render",
            "SHOT010_render",
        ]

    def test_search_treats_percent_and_underscore_literally(self, client: TestClient) -> None:
        assert _names(client.get("/jobs?q=_B_")) == ["SEQ_B_030"]
        assert _names(client.get("/jobs?q=%25")) == []

    def test_filters_combine_with_and(self, client: TestClient) -> None:
        assert _names(client.get("/jobs?status=dead&priority=normal")) == [
            "SEQ_B_030",
            "SHOT020_render",
        ]
        assert _names(client.get("/jobs?q=SHOT&status=dead")) == ["SHOT020_render"]

    def test_the_total_follows_the_filters(self, client: TestClient) -> None:
        assert client.get("/jobs?status=pending").headers["X-Total-Count"] == "2"

    @pytest.mark.parametrize("query", ["limit=0", "limit=501", "offset=-1", "limit=x"])
    def test_bad_parameters_are_rejected(self, client: TestClient, query: str) -> None:
        assert client.get(f"/jobs?{query}").status_code == 422

    def test_an_unknown_status_or_priority_gives_an_empty_list_not_an_error(
        self, client: TestClient
    ) -> None:
        assert client.get("/jobs?status=nope").json() == []
        assert client.get("/jobs?priority=urgent").json() == []

    def test_the_header_is_exposed_to_browsers(self, client: TestClient) -> None:
        response = client.options(
            "/jobs",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        simple = client.get("/jobs", headers={"Origin": "http://localhost:5173"})

        assert "x-total-count" in simple.headers["access-control-expose-headers"].lower()
        assert response.status_code == 200
