from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.adapters.outbound.postgres_session_repository import PostgresSessionRepository
from app.domain.entities.message import ChatMessage
from app.domain.exceptions.errors import SessionStoreError


class _AsyncContext:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, state: dict, fail_execute: bool = False) -> None:
        self._state = state
        self._fail_execute = fail_execute

    def transaction(self):
        return _AsyncContext(None)

    async def fetch(self, query: str, session_id: str):
        del query
        session = self._state["sessions"].get(session_id)
        if session is None:
            return []

        expires_at = session["expires_at"]
        if expires_at is not None and expires_at <= datetime.now(timezone.utc):
            return []

        rows = self._state["messages"].get(session["id"], [])
        sorted_rows = sorted(rows, key=lambda row: row["turn_index"])
        return [{"role": row["role"], "content": row["content"]} for row in sorted_rows]

    async def fetchval(self, query: str, *args):
        if "SELECT 1" in query:
            return 1

        if "INSERT INTO chat_sessions" in query:
            session_id, expires_at = args
            session = self._state["sessions"].get(session_id)
            if session is None:
                self._state["next_session_pk"] += 1
                session = {
                    "id": self._state["next_session_pk"],
                    "session_id": session_id,
                    "expires_at": expires_at,
                }
                self._state["sessions"][session_id] = session
            else:
                session["expires_at"] = expires_at
            return session["id"]

        raise AssertionError(f"unexpected fetchval query: {query}")

    async def execute(self, query: str, *args):
        if self._fail_execute:
            raise RuntimeError("db execute failed")

        if "DELETE FROM chat_messages" in query:
            session_pk = args[0]
            self._state["messages"][session_pk] = []
            return "DELETE"

        raise AssertionError(f"unexpected execute query: {query}")

    async def executemany(self, query: str, payload):
        if self._fail_execute:
            raise RuntimeError("db executemany failed")

        if "INSERT INTO chat_messages" not in query:
            raise AssertionError(f"unexpected executemany query: {query}")

        for session_pk, turn_index, role, content in payload:
            self._state["messages"].setdefault(session_pk, []).append(
                {
                    "turn_index": turn_index,
                    "role": role,
                    "content": content,
                }
            )


class _FakePool:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn
        self.closed = False

    def acquire(self):
        return _AsyncContext(self._conn)

    async def close(self) -> None:
        self.closed = True


def _build_repo(monkeypatch: pytest.MonkeyPatch, *, fail_execute: bool = False, expiration_sec: int = 300):
    state = {"next_session_pk": 0, "sessions": {}, "messages": {}}
    pool = _FakePool(_FakeConn(state, fail_execute=fail_execute))

    async def _fake_create_pool(**kwargs):
        del kwargs
        return pool

    monkeypatch.setattr(
        "app.adapters.outbound.postgres_session_repository.asyncpg.create_pool",
        _fake_create_pool,
    )

    repo = PostgresSessionRepository(
        dsn="postgresql://app:app@localhost:5432/app",
        min_pool_size=1,
        max_pool_size=5,
        expiration_sec=expiration_sec,
        max_history_turns=2,
    )
    return repo, state, pool


@pytest.mark.asyncio
async def test_postgres_repository_set_get_and_trim(monkeypatch: pytest.MonkeyPatch) -> None:
    repo, _, _ = _build_repo(monkeypatch)
    messages = [
        ChatMessage(role="user", content="u1"),
        ChatMessage(role="assistant", content="a1"),
        ChatMessage(role="user", content="u2"),
        ChatMessage(role="assistant", content="a2"),
        ChatMessage(role="user", content="u3"),
        ChatMessage(role="assistant", content="a3"),
    ]

    await repo.set_history("session-1", messages)
    history = await repo.get_history("session-1")

    assert [m.content for m in history] == ["u2", "a2", "u3", "a3"]

    await repo.close()


@pytest.mark.asyncio
async def test_postgres_repository_applies_expiration_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    repo, _, _ = _build_repo(monkeypatch, expiration_sec=-1)

    await repo.set_history(
        "session-expired",
        [ChatMessage(role="user", content="hello"), ChatMessage(role="assistant", content="hi")],
    )
    history = await repo.get_history("session-expired")

    assert history == []
    await repo.close()


@pytest.mark.asyncio
async def test_postgres_repository_maps_db_failure_to_session_store_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, _, _ = _build_repo(monkeypatch, fail_execute=True)

    with pytest.raises(SessionStoreError):
        await repo.set_history(
            "session-error",
            [ChatMessage(role="user", content="hello"), ChatMessage(role="assistant", content="hi")],
        )

    await repo.close()


@pytest.mark.asyncio
async def test_postgres_repository_ping_returns_false_when_pool_creation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _raise_create_pool(**kwargs):
        del kwargs
        raise RuntimeError("db down")

    monkeypatch.setattr(
        "app.adapters.outbound.postgres_session_repository.asyncpg.create_pool",
        _raise_create_pool,
    )

    repo = PostgresSessionRepository(
        dsn="postgresql://app:app@localhost:5432/app",
        min_pool_size=1,
        max_pool_size=5,
        expiration_sec=300,
        max_history_turns=2,
    )

    assert await repo.ping() is False

