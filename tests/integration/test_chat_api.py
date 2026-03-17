from fastapi.testclient import TestClient

from app.common.config.settings import Settings
from app.main import app, create_app


def test_chat_api_text_audio() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/chat",
            json={
                "session_id": "session-a",
                "message": "테스트",
                "response_mode": "text_audio",
                "voice_id": "ko_female_1",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["response_mode"] == "text_audio"
    assert data["data"]["audio_url"] is not None
    assert "request_id" in data
    assert "trace_id" in data


def test_chat_api_error_contract_on_provider_failure() -> None:
    failing_settings = Settings(
        LLM_PROVIDER="vllm",
        VLLM_BASE_URL="http://localhost:65501",
        VLLM_CONNECT_TIMEOUT_SEC=0.01,
        VLLM_READ_TIMEOUT_SEC=0.01,
        TTS_PROVIDER="stub",
        SESSION_BACKEND="memory",
        HTTP_RETRY_COUNT=0,
    )
    failing_app = create_app(failing_settings)

    with TestClient(failing_app) as client:
        resp = client.post(
            "/api/v1/chat",
            json={
                "session_id": "session-a",
                "message": "실패 유도",
                "response_mode": "text",
            },
        )

    assert resp.status_code == 503
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] in {"LLM_TIMEOUT", "LLM_BAD_RESPONSE"}
    assert "request_id" in body["error"]
    assert "trace_id" in body["error"]


def test_chat_api_validation_error_contract() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/chat",
            json={
                "session_id": "",
                "message": "",
                "response_mode": "text",
            },
        )

    assert resp.status_code == 422
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == "INVALID_ARGUMENT"
    assert "request_id" in body["error"]
    assert "trace_id" in body["error"]
