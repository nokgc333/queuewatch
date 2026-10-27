"""コンテナの構成(Redis を公開しない、非 root、ヘルスチェック)が、実態と合っていることのテスト。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEV_SERVER_COMMAND = "npm run " + "dev"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_the_default_compose_file_does_not_publish_redis() -> None:
    compose = _read("docker-compose.yml")
    redis_block = compose.split("  backend:")[0]

    assert "ports:" not in redis_block
    assert "--requirepass" in redis_block


def test_the_dev_override_is_the_only_place_that_publishes_redis() -> None:
    override = _read("docker-compose.dev.yml")

    assert '"127.0.0.1:6379:6379"' in override


def test_published_ports_are_bound_to_localhost() -> None:
    for name in ("docker-compose.yml", "docker-compose.dev.yml"):
        for port in re.findall(r'- "([^"]*:\d+:\d+)"', _read(name)):
            assert port.startswith("127.0.0.1:"), (name, port)


def test_the_broker_url_carries_the_redis_password() -> None:
    compose = _read("docker-compose.yml")

    assert "redis://:${REDIS_PASSWORD" in compose
    assert "@redis:6379/0" in compose


def test_the_dashboard_is_served_by_nginx_without_root_and_with_a_csp() -> None:
    dockerfile = _read("frontend/Dockerfile")
    nginx = _read("frontend/nginx/default.conf.template")

    assert "nginx-unprivileged" in dockerfile
    assert DEV_SERVER_COMMAND not in dockerfile.split("AS production")[1]
    assert "Content-Security-Policy" in nginx
    assert "script-src 'self'" in nginx
    assert "frame-ancestors 'none'" in nginx


def test_the_backend_image_is_hash_locked_and_non_root() -> None:
    dockerfile = _read("backend/Dockerfile")

    assert "--require-hashes" in dockerfile
    assert "USER queuewatch" in dockerfile
    assert "HEALTHCHECK" in dockerfile


def test_every_queuewatch_variable_the_backend_reads_is_in_the_example_file() -> None:
    used: set[str] = set()
    for path in (ROOT / "backend" / "app").rglob("*.py"):
        used |= set(re.findall(r"QUEUEWATCH_[A-Z_]+", path.read_text(encoding="utf-8")))

    example = _read(".env.example")

    assert sorted(n for n in used if n not in example) == []
