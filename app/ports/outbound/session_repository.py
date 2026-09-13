from typing import Protocol

from app.domain.entities.message import ChatMessage


class SessionRepositoryPort(Protocol):
    async def get_history(self, session_id: str) -> list[ChatMessage]:
        ...

    async def append_messages(
        self,
        session_id: str,
        messages: list[ChatMessage],
        max_messages: int | None = None,
    ) -> None:
        """히스토리 끝에 메시지를 원자적으로 덧붙인다.

        max_messages 가 주어지면 덧붙인 뒤 최근 N개만 남기고 잘라낸다.
        읽고-쓰기 왕복 없이 저장소 안에서 처리해야 동시 요청에서 턴이 유실되지 않는다.
        """
        ...

    async def set_history(self, session_id: str, messages: list[ChatMessage]) -> None:
        ...

    async def ping(self) -> bool:
        ...

    async def close(self) -> None:
        ...
