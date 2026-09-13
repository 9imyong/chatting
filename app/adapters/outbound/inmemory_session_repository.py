import asyncio
from collections import defaultdict

from app.domain.entities.message import ChatMessage
from app.ports.outbound.session_repository import SessionRepositoryPort


class InMemorySessionRepository(SessionRepositoryPort):
    def __init__(self) -> None:
        self._store: dict[str, list[ChatMessage]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        return list(self._store.get(session_id, []))

    async def append_messages(
        self,
        session_id: str,
        messages: list[ChatMessage],
        max_messages: int | None = None,
    ) -> None:
        if not messages:
            return
        async with self._lock:
            bucket = self._store[session_id]
            bucket.extend(messages)
            if max_messages is not None:
                if max_messages <= 0:
                    self._store[session_id] = []
                elif len(bucket) > max_messages:
                    self._store[session_id] = bucket[-max_messages:]

    async def set_history(self, session_id: str, messages: list[ChatMessage]) -> None:
        async with self._lock:
            self._store[session_id] = list(messages)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None
