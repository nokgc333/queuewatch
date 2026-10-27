from __future__ import annotations

import hmac
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum

from fastapi import Depends, HTTPException, Request, status

AUTH_MODE_LOCAL = "local"
AUTH_MODE_TOKEN = "token"
MIN_TOKEN_LENGTH = 12


class Role(IntEnum):
    VIEWER = 1
    EDITOR = 2
    ADMIN = 3


@dataclass(frozen=True)
class AuthSettings:
    mode: str
    tokens: tuple[tuple[Role, bytes], ...] = field(default_factory=tuple)


def _parse_tokens(raw: str) -> tuple[tuple[Role, bytes], ...]:
    entries: list[tuple[Role, bytes]] = []
    seen: set[bytes] = set()
    for item in filter(None, (part.strip() for part in raw.split(","))):
        role_name, separator, token = item.partition("=")
        if not separator:
            raise ValueError("QUEUEWATCH_API_TOKENS entries must look like 'role=token'")
        try:
            role = Role[role_name.strip().upper()]
        except KeyError as exc:
            raise ValueError(
                f"QUEUEWATCH_API_TOKENS has an unknown role '{role_name.strip()}' "
                "(expected viewer, editor or admin)"
            ) from exc
        encoded = token.strip().encode("utf-8")
        if len(encoded) < MIN_TOKEN_LENGTH:
            raise ValueError(
                f"QUEUEWATCH_API_TOKENS tokens must be at least {MIN_TOKEN_LENGTH} characters"
            )
        if encoded in seen:
            raise ValueError("QUEUEWATCH_API_TOKENS must not reuse a token for several roles")
        seen.add(encoded)
        entries.append((role, encoded))
    return tuple(entries)


def load_auth_settings() -> AuthSettings:
    mode = os.environ.get("QUEUEWATCH_AUTH_MODE", AUTH_MODE_LOCAL)
    if mode == AUTH_MODE_LOCAL:
        return AuthSettings(mode=mode)
    if mode != AUTH_MODE_TOKEN:
        raise ValueError(
            f"QUEUEWATCH_AUTH_MODE must be '{AUTH_MODE_LOCAL}' or '{AUTH_MODE_TOKEN}', got '{mode}'"
        )
    tokens = _parse_tokens(os.environ.get("QUEUEWATCH_API_TOKENS", ""))
    if not tokens:
        raise ValueError("QUEUEWATCH_API_TOKENS must define at least one token in token mode")
    return AuthSettings(mode=mode, tokens=tokens)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def authenticate(request: Request) -> Role:
    settings = load_auth_settings()
    if settings.mode == AUTH_MODE_LOCAL:
        return Role.ADMIN

    scheme, _, credential = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not credential.strip():
        raise _unauthorized()

    presented = credential.strip().encode("utf-8")
    matched: Role | None = None
    for role, token in settings.tokens:
        if hmac.compare_digest(presented, token):
            matched = role
    if matched is None:
        raise _unauthorized()
    return matched


def require_role(minimum: Role) -> Callable[[Role], Role]:
    def dependency(role: Role = Depends(authenticate)) -> Role:
        if role < minimum:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return role

    return dependency


requires_viewer = Depends(require_role(Role.VIEWER))
requires_editor = Depends(require_role(Role.EDITOR))
requires_admin = Depends(require_role(Role.ADMIN))
