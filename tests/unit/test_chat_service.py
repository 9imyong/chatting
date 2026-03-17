import pytest

from app.adapters.outbound.gptsovits_client_stub import GPTSoVITSStubClient
from app.adapters.outbound.inmemory_session_repository import InMemorySessionRepository
from app.adapters.outbound.vllm_client_stub import VLLMStubClient
from app.application.services.chat_orchestration_service import ChatOrchestrationService


@pytest.mark.asyncio
async def test_chat_service_text_only() -> None:
    service = ChatOrchestrationService(
        llm_client=VLLMStubClient(),
        tts_client=GPTSoVITSStubClient(),
        session_repo=InMemorySessionRepository(),
        max_history_turns=10,
    )

    result = await service.chat("s1", "hello", generate_audio=False, voice_id=None)

    assert result.text.startswith("stub-vllm-reply")
    assert result.audio_url is None


@pytest.mark.asyncio
async def test_chat_service_stores_session_history() -> None:
    repo = InMemorySessionRepository()
    service = ChatOrchestrationService(
        llm_client=VLLMStubClient(),
        tts_client=GPTSoVITSStubClient(),
        session_repo=repo,
        max_history_turns=10,
    )

    await service.chat("s2", "first", generate_audio=False, voice_id=None)
    await service.chat("s2", "second", generate_audio=False, voice_id=None)

    history = await repo.get_history("s2")
    assert len(history) == 4
    assert history[0].role == "user"
    assert history[-1].role == "assistant"


@pytest.mark.asyncio
async def test_chat_service_trims_history_by_turn() -> None:
    repo = InMemorySessionRepository()
    service = ChatOrchestrationService(
        llm_client=VLLMStubClient(),
        tts_client=GPTSoVITSStubClient(),
        session_repo=repo,
        max_history_turns=1,
    )

    await service.chat("s3", "first", generate_audio=False, voice_id=None)
    await service.chat("s3", "second", generate_audio=False, voice_id=None)

    history = await repo.get_history("s3")
    assert len(history) == 2
    assert history[0].content == "second"
    assert history[0].role == "user"
    assert history[1].role == "assistant"
