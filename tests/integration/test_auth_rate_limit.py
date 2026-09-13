from __future__ import annotations

from fastapi.testclient import TestClient

from app.common.config.settings import Settings
from app.main import create_app


def _chat_payload() -> dict:
    return {
        "session_id": "tenant-session",
        "message": "hello",
        "response_mode": "text",
    }


def test_chat_requires_authorization_when_enabled() -> None:
    app = create_app(
        Settings(
            AUTH_ENABLED=True,
            AUTH_TENANT_API_KEYS="tenant_a:token_a",
            RATE_LIMIT_ENABLED=False,
        )
    )
    with TestClient(app) as client:
        resp = client.post("/api/v1/chat", json=_chat_payload())

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_chat_unauthorized_with_invalid_api_key() -> None:
    """자격증명이 틀린 경우는 401 이다.

    403 은 인증은 성공했으나 해당 리소스 권한이 없을 때 쓴다.
    """
    app = create_app(
        Settings(
            AUTH_ENABLED=True,
            AUTH_TENANT_API_KEYS="tenant_a:token_a",
            RATE_LIMIT_ENABLED=False,
        )
    )
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/chat",
            json=_chat_payload(),
            headers={"Authorization": "Bearer wrong"},
        )

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


def test_repeated_auth_failures_are_rate_limited() -> None:
    """인증 실패에도 상한이 걸려야 API 키 대입을 막을 수 있다."""
    app = create_app(
        Settings(
            AUTH_ENABLED=True,
            AUTH_TENANT_API_KEYS="tenant_a:token_a",
            RATE_LIMIT_ENABLED=True,
            RATE_LIMIT_BACKEND="memory",
            AUTH_FAILURE_LIMIT_PER_WINDOW=2,
            RATE_LIMIT_WINDOW_SEC=60,
        )
    )
    statuses = []
    with TestClient(app) as client:
        for _ in range(4):
            resp = client.post(
                "/api/v1/chat",
                json=_chat_payload(),
                headers={"Authorization": "Bearer wrong"},
            )
            statuses.append(resp.status_code)

    assert statuses[0] == 401
    assert 429 in statuses, f"인증 실패가 제한되지 않았다: {statuses}"


def test_tenant_rate_limit_exceeded() -> None:
    app = create_app(
        Settings(
            AUTH_ENABLED=True,
            AUTH_TENANT_API_KEYS="tenant_a:token_a",
            RATE_LIMIT_ENABLED=True,
            RATE_LIMIT_BACKEND="memory",
            RATE_LIMIT_WINDOW_SEC=60,
            RATE_LIMIT_REQUESTS_PER_WINDOW=1,
        )
    )
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/chat",
            json=_chat_payload(),
            headers={"Authorization": "Bearer token_a"},
        )
        second = client.post(
            "/api/v1/chat",
            json=_chat_payload(),
            headers={"Authorization": "Bearer token_a"},
        )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_tenant_rate_limit_isolated_between_tenants() -> None:
    app = create_app(
        Settings(
            AUTH_ENABLED=True,
            AUTH_TENANT_API_KEYS="tenant_a:token_a,tenant_b:token_b",
            RATE_LIMIT_ENABLED=True,
            RATE_LIMIT_BACKEND="memory",
            RATE_LIMIT_WINDOW_SEC=60,
            RATE_LIMIT_REQUESTS_PER_WINDOW=1,
            RATE_LIMIT_TENANT_OVERRIDES="tenant_b:2",
        )
    )
    with TestClient(app) as client:
        a1 = client.post("/api/v1/chat", json=_chat_payload(), headers={"Authorization": "Bearer token_a"})
        a2 = client.post("/api/v1/chat", json=_chat_payload(), headers={"Authorization": "Bearer token_a"})
        b1 = client.post("/api/v1/chat", json=_chat_payload(), headers={"Authorization": "Bearer token_b"})
        b2 = client.post("/api/v1/chat", json=_chat_payload(), headers={"Authorization": "Bearer token_b"})

    assert a1.status_code == 200
    assert a2.status_code == 429
    assert b1.status_code == 200
    assert b2.status_code == 200

