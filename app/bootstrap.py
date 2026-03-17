from dataclasses import dataclass

from app.adapters.outbound.gptsovits_client_stub import GPTSoVITSStubClient
from app.adapters.outbound.gptsovits_http_client import GPTSoVITSHTTPClient
from app.adapters.outbound.inmemory_session_repository import InMemorySessionRepository
from app.adapters.outbound.redis_session_repository import RedisSessionRepository
from app.adapters.outbound.vllm_client_stub import VLLMStubClient
from app.adapters.outbound.vllm_http_client import VLLMHTTPClient
from app.application.services.chat_orchestration_service import ChatOrchestrationService
from app.common.config.settings import Settings
from app.ports.outbound.llm_client import LLMClientPort
from app.ports.outbound.session_repository import SessionRepositoryPort
from app.ports.outbound.tts_client import TTSClientPort


@dataclass
class AppContainer:
    settings: Settings
    llm_client: LLMClientPort
    tts_client: TTSClientPort
    session_repo: SessionRepositoryPort
    chat_service: ChatOrchestrationService


async def build_container(settings: Settings) -> AppContainer:
    session_repo = _build_session_repo(settings)
    llm_client = _build_llm_client(settings)
    tts_client = _build_tts_client(settings)
    chat_service = ChatOrchestrationService(
        llm_client=llm_client,
        tts_client=tts_client,
        session_repo=session_repo,
        max_history_turns=settings.MAX_HISTORY_TURNS,
    )
    return AppContainer(
        settings=settings,
        llm_client=llm_client,
        tts_client=tts_client,
        session_repo=session_repo,
        chat_service=chat_service,
    )


async def close_container(container: AppContainer) -> None:
    await container.llm_client.close()
    await container.tts_client.close()
    await container.session_repo.close()


def _build_llm_client(settings: Settings) -> LLMClientPort:
    if settings.LLM_PROVIDER == "stub":
        return VLLMStubClient()
    if settings.LLM_PROVIDER == "vllm":
        return VLLMHTTPClient(
            base_url=settings.VLLM_BASE_URL,
            model=settings.VLLM_MODEL,
            connect_timeout_sec=settings.VLLM_CONNECT_TIMEOUT_SEC,
            read_timeout_sec=settings.VLLM_READ_TIMEOUT_SEC,
            retry_count=settings.HTTP_RETRY_COUNT,
            retry_base_delay_sec=settings.HTTP_RETRY_BASE_DELAY_SEC,
            retry_max_delay_sec=settings.HTTP_RETRY_MAX_DELAY_SEC,
            retry_jitter_sec=settings.HTTP_RETRY_JITTER_SEC,
        )
    raise ValueError(f"unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")


def _build_tts_client(settings: Settings) -> TTSClientPort:
    if settings.TTS_PROVIDER == "stub":
        return GPTSoVITSStubClient()
    if settings.TTS_PROVIDER == "gptsovits":
        return GPTSoVITSHTTPClient(
            base_url=settings.GPT_SOVITS_BASE_URL,
            connect_timeout_sec=settings.GPT_SOVITS_CONNECT_TIMEOUT_SEC,
            read_timeout_sec=settings.GPT_SOVITS_READ_TIMEOUT_SEC,
            retry_count=settings.HTTP_RETRY_COUNT,
            retry_base_delay_sec=settings.HTTP_RETRY_BASE_DELAY_SEC,
            retry_max_delay_sec=settings.HTTP_RETRY_MAX_DELAY_SEC,
            retry_jitter_sec=settings.HTTP_RETRY_JITTER_SEC,
        )
    raise ValueError(f"unsupported TTS_PROVIDER: {settings.TTS_PROVIDER}")


def _build_session_repo(settings: Settings) -> SessionRepositoryPort:
    if settings.SESSION_BACKEND == "memory":
        return InMemorySessionRepository()
    if settings.SESSION_BACKEND == "redis":
        return RedisSessionRepository(redis_url=settings.REDIS_URL, ttl_sec=settings.SESSION_TTL_SEC)
    raise ValueError(f"unsupported SESSION_BACKEND: {settings.SESSION_BACKEND}")
