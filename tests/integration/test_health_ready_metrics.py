from fastapi.testclient import TestClient

from app.common.config.settings import Settings
from app.main import app, create_app


def test_health_ready_metrics_ok() -> None:
    with TestClient(app) as client:
        client.post(
            "/api/v1/chat",
            json={
                "session_id": "session-metrics",
                "message": "metrics",
                "response_mode": "text",
            },
        )
        health = client.get("/health")
        ready = client.get("/ready")
        metrics = client.get("/metrics")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "ok"
    assert body["dependencies"]["llm"]["status"] == "ok"
    assert body["dependencies"]["tts"]["status"] == "ok"
    assert body["dependencies"]["session_store"]["status"] == "ok"

    assert metrics.status_code == 200
    assert "app_request_total" in metrics.text
    assert "chat_request_total" in metrics.text
    assert "provider_latency_seconds" in metrics.text
    assert "readiness_probe_latency_seconds" in metrics.text


def test_ready_degraded_when_one_dependency_down() -> None:
    degraded_settings = Settings(
        LLM_PROVIDER="stub",
        TTS_PROVIDER="stub",
        SESSION_BACKEND="redis",
        REDIS_URL="redis://localhost:6399/0",
    )
    degraded_app = create_app(degraded_settings)

    with TestClient(degraded_app) as client:
        ready = client.get("/ready")

    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["session_store"]["status"] == "fail"
    assert body["dependencies"]["session_store"]["reason"] is not None


def test_ready_fail_when_all_dependencies_down() -> None:
    fail_settings = Settings(
        LLM_PROVIDER="vllm",
        VLLM_BASE_URL="http://localhost:65501",
        VLLM_CONNECT_TIMEOUT_SEC=0.01,
        VLLM_READ_TIMEOUT_SEC=0.01,
        TTS_PROVIDER="gptsovits",
        GPT_SOVITS_BASE_URL="http://localhost:65502",
        GPT_SOVITS_CONNECT_TIMEOUT_SEC=0.01,
        GPT_SOVITS_READ_TIMEOUT_SEC=0.01,
        SESSION_BACKEND="redis",
        REDIS_URL="redis://localhost:6399/0",
    )
    fail_app = create_app(fail_settings)

    with TestClient(fail_app) as client:
        ready = client.get("/ready")

    assert ready.status_code == 503
    body = ready.json()
    assert body["status"] == "fail"
    assert body["dependencies"]["llm"]["status"] == "fail"
    assert body["dependencies"]["tts"]["status"] == "fail"
    assert body["dependencies"]["session_store"]["status"] == "fail"


def test_ready_degraded_when_postgres_dependency_down() -> None:
    degraded_settings = Settings(
        LLM_PROVIDER="stub",
        TTS_PROVIDER="stub",
        SESSION_BACKEND="postgres",
        POSTGRES_DSN="postgresql://app:app@localhost:65503/app",
    )
    degraded_app = create_app(degraded_settings)

    with TestClient(degraded_app) as client:
        ready = client.get("/ready")

    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["llm"]["status"] == "ok"
    assert body["dependencies"]["tts"]["status"] == "ok"
    assert body["dependencies"]["session_store"]["status"] == "fail"
    assert body["dependencies"]["session_store"]["reason"] is not None


def test_ready_includes_rate_limiter_when_enabled() -> None:
    ready_settings = Settings(
        LLM_PROVIDER="stub",
        TTS_PROVIDER="stub",
        SESSION_BACKEND="memory",
        RATE_LIMIT_ENABLED=True,
        RATE_LIMIT_BACKEND="memory",
    )
    ready_app = create_app(ready_settings)

    with TestClient(ready_app) as client:
        ready = client.get("/ready")

    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "ok"
    assert body["dependencies"]["rate_limiter"]["status"] == "ok"
