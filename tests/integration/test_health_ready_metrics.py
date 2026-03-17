from fastapi.testclient import TestClient

from app.common.config.settings import Settings
from app.main import app, create_app


def test_health_ready_metrics() -> None:
    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")
        metrics = client.get("/metrics")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.status_code == 200
    body = ready.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ready"
    assert body["data"]["dependencies"]["bootstrap"] == "up"
    assert "session_repository" in body["data"]["dependencies"]
    assert metrics.status_code == 200
    assert "app_request_total" in metrics.text


def test_ready_returns_503_when_dependency_down() -> None:
    down_settings = Settings(
        LLM_PROVIDER="stub",
        TTS_PROVIDER="stub",
        SESSION_BACKEND="redis",
        REDIS_URL="redis://localhost:6399/0",
    )
    down_app = create_app(down_settings)

    with TestClient(down_app) as client:
        ready = client.get("/ready")

    assert ready.status_code == 503
    body = ready.json()
    assert body["success"] is False
    assert body["data"]["status"] == "not_ready"
    assert body["data"]["dependencies"]["session_repository"] == "down"
