from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="env/.env.dev",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    APP_NAME: str = "chat-model-serving"
    APP_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    LLM_PROVIDER: str = "stub"  # stub | vllm
    TTS_PROVIDER: str = "stub"  # stub | gptsovits
    SESSION_BACKEND: str = "memory"  # memory | redis

    VLLM_BASE_URL: str = "http://localhost:8001"
    VLLM_MODEL: str = "default"
    VLLM_CONNECT_TIMEOUT_SEC: float = 2.0
    VLLM_READ_TIMEOUT_SEC: float = 10.0

    GPT_SOVITS_BASE_URL: str = "http://localhost:9880"
    GPT_SOVITS_CONNECT_TIMEOUT_SEC: float = 2.0
    GPT_SOVITS_READ_TIMEOUT_SEC: float = 12.0

    HTTP_RETRY_COUNT: int = 2
    HTTP_RETRY_BASE_DELAY_SEC: float = 0.2
    HTTP_RETRY_MAX_DELAY_SEC: float = 2.0
    HTTP_RETRY_JITTER_SEC: float = 0.1

    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TTL_SEC: int = 3600
    MAX_HISTORY_TURNS: int = 10

    REQUEST_TIMEOUT_SEC: float = 15.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
