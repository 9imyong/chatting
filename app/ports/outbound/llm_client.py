from typing import Protocol

from app.domain.entities.message import ChatMessage


class LLMClientPort(Protocol):
    async def generate(self, messages: list[ChatMessage]) -> str:
        ...

    async def ping(self) -> bool:
        ...

    async def close(self) -> None:
        ...
