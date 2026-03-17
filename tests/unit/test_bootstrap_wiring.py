import pytest

from app.adapters.outbound.gptsovits_client_stub import GPTSoVITSStubClient
from app.adapters.outbound.inmemory_session_repository import InMemorySessionRepository
from app.adapters.outbound.postgres_session_repository import PostgresSessionRepository
from app.adapters.outbound.vllm_client_stub import VLLMStubClient
from app.bootstrap import build_container, close_container
from app.common.config.settings import Settings


@pytest.mark.asyncio
async def test_build_container_with_stub_and_memory() -> None:
    settings = Settings(LLM_PROVIDER="stub", TTS_PROVIDER="stub", SESSION_BACKEND="memory")
    container = await build_container(settings)

    assert isinstance(container.llm_client, VLLMStubClient)
    assert isinstance(container.tts_client, GPTSoVITSStubClient)
    assert isinstance(container.session_repo, InMemorySessionRepository)

    await close_container(container)


@pytest.mark.asyncio
async def test_build_container_with_stub_and_postgres_repo() -> None:
    settings = Settings(
        LLM_PROVIDER="stub",
        TTS_PROVIDER="stub",
        SESSION_BACKEND="postgres",
        POSTGRES_DSN="postgresql://app:app@localhost:5432/app",
    )
    container = await build_container(settings)

    assert isinstance(container.llm_client, VLLMStubClient)
    assert isinstance(container.tts_client, GPTSoVITSStubClient)
    assert isinstance(container.session_repo, PostgresSessionRepository)

    await close_container(container)
