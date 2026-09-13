"""동시 요청에서 대화 턴이 유실되지 않는지 검증한다.

읽고-수정하고-덮어쓰는(read-modify-write) 방식이면 두 요청이 같은 히스토리를
읽은 뒤 각자 통째로 저장해 한쪽 턴이 사라진다. 이 테스트가 그 회귀를 막는다.
"""
from __future__ import annotations

import asyncio

import pytest

from app.adapters.outbound.gptsovits_client_stub import GPTSoVITSStubClient
from app.adapters.outbound.inmemory_session_repository import InMemorySessionRepository
from app.adapters.outbound.vllm_client_stub import VLLMStubClient
from app.application.services.chat_orchestration_service import ChatOrchestrationService
from app.domain.entities.message import ChatMessage


def _build_service(repo: InMemorySessionRepository) -> ChatOrchestrationService:
    return ChatOrchestrationService(
        llm_client=VLLMStubClient(),
        tts_client=GPTSoVITSStubClient(),
        session_repo=repo,
        max_history_turns=10,
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
    # 요청 2건 x (user + assistant) = 4개. 하나라도 유실되면 2개가 된다.
    assert len(history) == 4
    user_messages = {msg.content for msg in history if msg.role == "user"}
    assert user_messages == {"first", "second"}


@pytest.mark.asyncio
async def test_concurrent_appends_are_atomic() -> None:
    repo = InMemorySessionRepository()

    await asyncio.gather(
        *[
            repo.append_messages("s", [ChatMessage(role="user", content=str(i))])
            for i in range(20)
        ]
    )

    history = await repo.get_history("s")
    assert len(history) == 20
    assert {msg.content for msg in history} == {str(i) for i in range(20)}


@pytest.mark.asyncio
async def test_history_is_trimmed_after_append() -> None:
    repo = InMemorySessionRepository()
    service = ChatOrchestrationService(
        llm_client=VLLMStubClient(),
        tts_client=GPTSoVITSStubClient(),
        session_repo=repo,
        max_history_turns=1,
        stream_chunk_size=12,
    )

    await service.chat("t", "first", generate_audio=False, voice_id=None)
    await service.chat("t", "second", generate_audio=False, voice_id=None)

    history = await repo.get_history("t")
    assert len(history) == 2
    assert history[0].content == "second"
    assert history[0].role == "user"
    assert history[1].role == "assistant"
