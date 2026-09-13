from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import asyncpg

from app.domain.entities.message import ChatMessage
from app.domain.exceptions.errors import SessionStoreError
from app.ports.outbound.session_repository import SessionRepositoryPort


class PostgresSessionRepository(SessionRepositoryPort):
    def __init__(
        self,
        dsn: str,
        min_pool_size: int,
        max_pool_size: int,
        expiration_sec: int,
        max_history_turns: int,
    ) -> None:
        self._dsn = dsn
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._expiration_sec = expiration_sec
        self._max_history_turns = max_history_turns
        self._pool: Optional[asyncpg.Pool] = None
        self._pool_lock = asyncio.Lock()

    async def _ensure_pool(self) -> asyncpg.Pool:
        # 락이 없으면 첫 동시 요청들이 각자 풀을 만들고, 마지막 것만 남아
        # 나머지 풀이 닫히지 않은 채 누수된다.
        if self._pool is not None:
            return self._pool
        async with self._pool_lock:
            if self._pool is None:
                self._pool = await asyncpg.create_pool(
                    dsn=self._dsn,
                    min_size=self._min_pool_size,
                    max_size=self._max_pool_size,
                )
        return self._pool

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        query = """
        SELECT m.role, m.content
          FROM chat_messages m
          JOIN chat_sessions s ON s.id = m.session_pk
         WHERE s.session_id = $1
           AND (s.expires_at IS NULL OR s.expires_at > now())
         ORDER BY m.turn_index ASC
        """
        try:
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, session_id)
            return [ChatMessage(role=row["role"], content=row["content"]) for row in rows]
        except Exception as exc:
            raise SessionStoreError("failed to load session history from postgres") from exc

    async def append_messages(
        self,
        session_id: str,
        messages: list[ChatMessage],
        max_messages: int | None = None,
    ) -> None:
        """세션 행을 잠그고 turn_index 를 이어 붙인다.

        이전 구현은 get_history -> set_history 왕복이라 동시 요청 시 한쪽 턴이
        통째로 사라졌다. 세션 행 FOR UPDATE 로 같은 세션의 append 를 직렬화한다.
        """
        if not messages:
            return

        upsert_session = """
        INSERT INTO chat_sessions (session_id, expires_at)
        VALUES ($1, $2)
        ON CONFLICT (session_id)
        DO UPDATE SET updated_at = now(), expires_at = EXCLUDED.expires_at
        RETURNING id
        """
        lock_session = "SELECT id FROM chat_sessions WHERE id = $1 FOR UPDATE"
        next_turn = "SELECT COALESCE(MAX(turn_index), -1) FROM chat_messages WHERE session_pk = $1"
        insert_message = """
        INSERT INTO chat_messages (session_pk, turn_index, role, content)
        VALUES ($1, $2, $3, $4)
        """
        trim_messages = """
        DELETE FROM chat_messages
         WHERE session_pk = $1
           AND turn_index <= $2
        """
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._expiration_sec)

        try:
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                async with conn.transaction():
                    session_pk = await conn.fetchval(upsert_session, session_id, expires_at)
                    await conn.fetchval(lock_session, session_pk)

                    last_index = await conn.fetchval(next_turn, session_pk)
                    payload = [
                        (session_pk, last_index + 1 + offset, msg.role, msg.content)
                        for offset, msg in enumerate(messages)
                    ]
                    await conn.executemany(insert_message, payload)

                    limit = self._resolve_max_messages(max_messages)
                    if limit is not None:
                        highest = last_index + len(messages)
                        await conn.execute(trim_messages, session_pk, highest - limit)
        except Exception as exc:
            raise SessionStoreError("failed to append session history to postgres") from exc

    def _resolve_max_messages(self, max_messages: int | None) -> int | None:
        if max_messages is not None:
            return max(0, max_messages)
        if self._max_history_turns > 0:
            return self._max_history_turns * 2
        return None

    async def set_history(self, session_id: str, messages: list[ChatMessage]) -> None:
        normalized = self._normalize_messages(messages)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._expiration_sec)

        upsert_session = """
        INSERT INTO chat_sessions (session_id, expires_at)
        VALUES ($1, $2)
        ON CONFLICT (session_id)
        DO UPDATE SET updated_at = now(), expires_at = EXCLUDED.expires_at
        RETURNING id
        """
        delete_messages = "DELETE FROM chat_messages WHERE session_pk = $1"
        insert_message = """
        INSERT INTO chat_messages (session_pk, turn_index, role, content)
        VALUES ($1, $2, $3, $4)
        """

        try:
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                async with conn.transaction():
                    session_pk = await conn.fetchval(upsert_session, session_id, expires_at)
                    await conn.execute(delete_messages, session_pk)
                    if normalized:
                        payload = [
                            (session_pk, idx, msg.role, msg.content)
                            for idx, msg in enumerate(normalized)
                        ]
                        await conn.executemany(insert_message, payload)
        except Exception as exc:
            raise SessionStoreError("failed to set session history in postgres") from exc

    async def ping(self) -> bool:
        try:
            pool = await self._ensure_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _normalize_messages(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        max_messages = max(0, self._max_history_turns * 2)
        if max_messages == 0:
            return []
        return list(messages[-max_messages:])
