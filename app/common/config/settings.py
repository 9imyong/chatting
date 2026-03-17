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
    SESSION_BACKEND: str = "memory"  # memory | redis | postgres

    VLLM_BASE_URL: str = "http://localhost:8001"
    VLLM_MODEL: str = "default"
    VLLM_TEMPERATURE: float = 0.7
    VLLM_MAX_TOKENS: int = 256
    VLLM_CONNECT_TIMEOUT_SEC: float = 2.0
    VLLM_READ_TIMEOUT_SEC: float = 10.0

    GPT_SOVITS_BASE_URL: str = "http://localhost:9880"
    GPT_SOVITS_CONNECT_TIMEOUT_SEC: float = 2.0
    GPT_SOVITS_READ_TIMEOUT_SEC: float = 12.0

    HTTP_RETRY_COUNT: int = 2
    HTTP_RETRY_BASE_DELAY_SEC: float = 0.2
    HTTP_RETRY_MAX_DELAY_SEC: float = 2.0
    HTTP_RETRY_JITTER_ENABLED: bool = True
    HTTP_RETRY_JITTER_RATIO: float = 0.25
    HTTP_RETRY_TOTAL_TIMEOUT_SEC: float = 8.0
    LLM_HTTP_RETRY_COUNT: int = -1
    TTS_HTTP_RETRY_COUNT: int = -1
    TTS_SYNTHESIS_IDEMPOTENT: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"
    SESSION_TTL_SEC: int = 3600
    POSTGRES_DSN: str = "postgresql://app:app@localhost:5432/app"
    POSTGRES_MIN_POOL_SIZE: int = 1
    POSTGRES_MAX_POOL_SIZE: int = 5
    SESSION_EXPIRATION_SEC: int = 86400
    MAX_HISTORY_TURNS: int = 10

    REQUEST_TIMEOUT_SEC: float = 15.0
    STREAM_TOTAL_TIMEOUT_SEC: float = 30.0
    STREAM_CHUNK_SIZE: int = 12

    AUTH_ENABLED: bool = False
    AUTH_DEFAULT_TENANT: str = "public"
    AUTH_TENANT_API_KEYS: str = ""

    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_BACKEND: str = "memory"  # memory | redis
    RATE_LIMIT_WINDOW_SEC: int = 60
    RATE_LIMIT_REQUESTS_PER_WINDOW: int = 60
    RATE_LIMIT_TENANT_OVERRIDES: str = ""
    RATE_LIMIT_FAIL_OPEN: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
