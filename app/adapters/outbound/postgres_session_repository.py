from __future__ import annotations

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

    async def _ensure_pool(self) -> asyncpg.Pool:
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

    async def append_messages(self, session_id: str, messages: list[ChatMessage]) -> None:
        try:
            current = await self.get_history(session_id)
            merged = [*current, *messages]
            await self.set_history(session_id, merged)
        except SessionStoreError:
            raise
        except Exception as exc:
            raise SessionStoreError("failed to append session history to postgres") from exc

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
