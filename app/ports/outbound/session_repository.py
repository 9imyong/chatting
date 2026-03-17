from typing import Protocol

from app.domain.entities.message import ChatMessage


class SessionRepositoryPort(Protocol):
    async def get_history(self, session_id: str) -> list[ChatMessage]:
        ...

    async def append_messages(self, session_id: str, messages: list[ChatMessage]) -> None:
        ...

    async def set_history(self, session_id: str, messages: list[ChatMessage]) -> None:
        ...

    async def ping(self) -> bool:
        ...

    async def close(self) -> None:
        ...
