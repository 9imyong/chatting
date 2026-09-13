"""동시 요청에서 대화 턴이 유실되지 않는지 검증한다.

히스토리를 읽어 합친 뒤 통째로 덮어쓰면, 두 요청이 같은 히스토리를 읽고 각자
저장해 한쪽 턴이 사라진다.

주의: 기본 스텁들은 await 안에 실제 중단점이 없어 asyncio.gather 로 묶어도
코루틴이 순차 실행된다. 그래서는 경합이 재현되지 않으므로, 여기서는 LLM 호출이
실제로 이벤트 루프에 양보하도록 만들어 읽기와 쓰기 사이를 벌린다.
"""
from __future__ import annotations

import asyncio

import pytest

from app.adapters.outbound.gptsovits_client_stub import GPTSoVITSStubClient
from app.adapters.outbound.inmemory_session_repository import InMemorySessionRepository
from app.application.services.chat_orchestration_service import ChatOrchestrationService
from app.domain.entities.message import ChatMessage
from app.ports.outbound.llm_client import LLMClientPort


class SuspendingLLMClient(LLMClientPort):
    """응답 전에 이벤트 루프에 양보하는 LLM 스텁.

    실제 네트워크 호출처럼 중단점을 만들어, 히스토리 읽기와 저장 사이에
    다른 요청이 끼어들 수 있게 한다.
    """

    async def generate(self, messages: list[ChatMessage]) -> str:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        await asyncio.sleep(0)
        return f"reply: {last_user}"

    async def generate_stream(self, messages: list[ChatMessage]):
        text = await self.generate(messages)
        yield text

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None


class RecordingSessionRepository(InMemorySessionRepository):
    """어떤 쓰기 경로를 썼는지 기록하는 저장소."""

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    async def append_messages(self, session_id, messages, max_messages=None) -> None:
        self.calls.append("append_messages")
        await super().append_messages(session_id, messages, max_messages)

    async def set_history(self, session_id, messages) -> None:
        self.calls.append("set_history")
        await super().set_history(session_id, messages)


def _build_service(repo: InMemorySessionRepository, max_history_turns: int = 10):
    return ChatOrchestrationService(
        llm_client=SuspendingLLMClient(),
        tts_client=GPTSoVITSStubClient(),
        session_repo=repo,
        max_history_turns=max_history_turns,
        stream_chunk_size=12,
    )


@pytest.mark.asyncio
async def test_concurrent_chats_do_not_lose_turns() -> None:
    repo = InMemorySessionRepository()
    service = _build_service(repo)

    await asyncio.gather(
        service.chat("shared", "first", generate_audio=False, voice_id=None),
        service.chat("shared", "second", generate_audio=False, voice_id=None),
    )

    history = await repo.get_history("shared")
    # 요청 2건 x (user + assistant) = 4개. 덮어쓰기 방식이면 2개로 줄어든다.
    assert len(history) == 4, f"턴이 유실됐다: {[m.content for m in history]}"
    assert {m.content for m in history if m.role == "user"} == {"first", "second"}


@pytest.mark.asyncio
async def test_service_appends_instead_of_overwriting_history() -> None:
    """서비스는 이번 턴만 덧붙여야 한다.

    히스토리 전체를 다시 쓰는 경로(set_history)는 동시 요청에서 유실을 만들고,
    저장소 입장에서도 턴 수에 비례한 쓰기를 유발한다.
    """
    repo = RecordingSessionRepository()
    service = _build_service(repo)

    await service.chat("s", "hello", generate_audio=False, voice_id=None)

    assert repo.calls == ["append_messages"], f"예상과 다른 쓰기 경로: {repo.calls}"


@pytest.mark.asyncio
async def test_concurrent_appends_keep_every_message() -> None:
    repo = InMemorySessionRepository()

    await asyncio.gather(
        *[
            repo.append_messages("s", [ChatMessage(role="user", content=str(i))])
            for i in range(20)
        ]
    )

    history = await repo.get_history("s")
    assert len(history) == 20
    assert {m.content for m in history} == {str(i) for i in range(20)}


@pytest.mark.asyncio
async def test_history_is_trimmed_after_append() -> None:
    repo = InMemorySessionRepository()
    service = _build_service(repo, max_history_turns=1)

    await service.chat("t", "first", generate_audio=False, voice_id=None)
    await service.chat("t", "second", generate_audio=False, voice_id=None)

    history = await repo.get_history("t")
    assert len(history) == 2
    assert history[0].content == "second"
    assert history[0].role == "user"
    assert history[1].role == "assistant"
