from collections import defaultdict

from app.domain.entities.message import ChatMessage
from app.ports.outbound.session_repository import SessionRepositoryPort


class InMemorySessionRepository(SessionRepositoryPort):
    def __init__(self) -> None:
        self._store: dict[str, list[ChatMessage]] = defaultdict(list)

    async def get_history(self, session_id: str) -> list[ChatMessage]:
        return list(self._store.get(session_id, []))

    async def append_messages(self, session_id: str, messages: list[ChatMessage]) -> None:
        self._store[session_id].extend(messages)

    async def set_history(self, session_id: str, messages: list[ChatMessage]) -> None:
        self._store[session_id] = list(messages)

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None
