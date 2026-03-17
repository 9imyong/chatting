from dataclasses import dataclass

from app.adapters.outbound.gptsovits_client_stub import GPTSoVITSStubClient
from app.adapters.outbound.gptsovits_http_client import GPTSoVITSHTTPClient
from app.adapters.outbound.inmemory_session_repository import InMemorySessionRepository
from app.adapters.outbound.postgres_session_repository import PostgresSessionRepository
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
        stream_chunk_size=settings.STREAM_CHUNK_SIZE,
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
        llm_retry_count = (
            settings.LLM_HTTP_RETRY_COUNT
            if settings.LLM_HTTP_RETRY_COUNT >= 0
            else settings.HTTP_RETRY_COUNT
        )
        return VLLMHTTPClient(
            base_url=settings.VLLM_BASE_URL,
            model=settings.VLLM_MODEL,
            temperature=settings.VLLM_TEMPERATURE,
            max_tokens=settings.VLLM_MAX_TOKENS,
            connect_timeout_sec=settings.VLLM_CONNECT_TIMEOUT_SEC,
            read_timeout_sec=settings.VLLM_READ_TIMEOUT_SEC,
            retry_count=llm_retry_count,
            retry_base_delay_sec=settings.HTTP_RETRY_BASE_DELAY_SEC,
            retry_max_delay_sec=settings.HTTP_RETRY_MAX_DELAY_SEC,
            retry_jitter_enabled=settings.HTTP_RETRY_JITTER_ENABLED,
            retry_jitter_ratio=settings.HTTP_RETRY_JITTER_RATIO,
            retry_total_timeout_sec=settings.HTTP_RETRY_TOTAL_TIMEOUT_SEC,
        )
    raise ValueError(f"unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")


def _build_tts_client(settings: Settings) -> TTSClientPort:
    if settings.TTS_PROVIDER == "stub":
        return GPTSoVITSStubClient()
    if settings.TTS_PROVIDER == "gptsovits":
        tts_retry_count = (
            settings.TTS_HTTP_RETRY_COUNT
            if settings.TTS_HTTP_RETRY_COUNT >= 0
            else settings.HTTP_RETRY_COUNT
        )
        return GPTSoVITSHTTPClient(
            base_url=settings.GPT_SOVITS_BASE_URL,
            connect_timeout_sec=settings.GPT_SOVITS_CONNECT_TIMEOUT_SEC,
            read_timeout_sec=settings.GPT_SOVITS_READ_TIMEOUT_SEC,
            retry_count=tts_retry_count,
            retry_base_delay_sec=settings.HTTP_RETRY_BASE_DELAY_SEC,
            retry_max_delay_sec=settings.HTTP_RETRY_MAX_DELAY_SEC,
            retry_jitter_enabled=settings.HTTP_RETRY_JITTER_ENABLED,
            retry_jitter_ratio=settings.HTTP_RETRY_JITTER_RATIO,
            retry_total_timeout_sec=settings.HTTP_RETRY_TOTAL_TIMEOUT_SEC,
            synthesis_idempotent=settings.TTS_SYNTHESIS_IDEMPOTENT,
        )
    raise ValueError(f"unsupported TTS_PROVIDER: {settings.TTS_PROVIDER}")


def _build_session_repo(settings: Settings) -> SessionRepositoryPort:
    if settings.SESSION_BACKEND == "memory":
        return InMemorySessionRepository()
    if settings.SESSION_BACKEND == "redis":
        return RedisSessionRepository(redis_url=settings.REDIS_URL, ttl_sec=settings.SESSION_TTL_SEC)
    if settings.SESSION_BACKEND == "postgres":
        return PostgresSessionRepository(
            dsn=settings.POSTGRES_DSN,
            min_pool_size=settings.POSTGRES_MIN_POOL_SIZE,
            max_pool_size=settings.POSTGRES_MAX_POOL_SIZE,
            expiration_sec=settings.SESSION_EXPIRATION_SEC,
            max_history_turns=settings.MAX_HISTORY_TURNS,
        )
    raise ValueError(f"unsupported SESSION_BACKEND: {settings.SESSION_BACKEND}")
