from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.common.config.settings import Settings
from app.main import app, create_app


def _collect_sse_events(client: TestClient, payload: dict) -> list[dict]:
    events: list[dict] = []
    with client.stream("POST", "/api/v1/chat/stream", json=payload) as resp:
        assert resp.status_code == 200
        current_event: str | None = None
        current_data: dict | None = None
        for line in resp.iter_lines():
            if not line:
                if current_event is not None and current_data is not None:
                    events.append({"event": current_event, "data": current_data})
                current_event = None
                current_data = None
                continue
            if line.startswith("event: "):
                current_event = line.replace("event: ", "", 1).strip()
            elif line.startswith("data: "):
                current_data = json.loads(line.replace("data: ", "", 1))
    return events


def test_chat_stream_success_sequence() -> None:
    with TestClient(app) as client:
        events = _collect_sse_events(
            client,
            {"session_id": "stream-s1", "message": "안녕", "response_mode": "text"},
        )

    assert events[0]["event"] == "start"
    assert events[0]["data"]["session_id"] == "stream-s1"
    assert "request_id" in events[0]["data"]
    assert "trace_id" in events[0]["data"]
    assert any(evt["event"] == "token" for evt in events)
    assert events[-1]["event"] == "done"
    assert events[-1]["data"]["finish_reason"] == "stop"


def test_chat_stream_provider_error_event() -> None:
    failing_settings = Settings(
        LLM_PROVIDER="vllm",
        VLLM_BASE_URL="http://localhost:65501",
        VLLM_CONNECT_TIMEOUT_SEC=0.01,
        VLLM_READ_TIMEOUT_SEC=0.01,
        TTS_PROVIDER="stub",
        SESSION_BACKEND="memory",
        HTTP_RETRY_COUNT=0,
        LLM_HTTP_RETRY_COUNT=0,
    )
    failing_app = create_app(failing_settings)

    with TestClient(failing_app) as client:
        events = _collect_sse_events(
            client,
            {"session_id": "stream-s2", "message": "실패", "response_mode": "text"},
        )

    assert events[0]["event"] == "start"
    assert events[-1]["event"] == "error"
    code = events[-1]["data"]["error"]["code"]
    assert code in {"LLM_TIMEOUT", "LLM_BAD_RESPONSE", "INTERNAL_ERROR"}


def test_chat_stream_disconnect_increments_metric() -> None:
    with TestClient(app) as client:
        with client.stream(
            "POST",
            "/api/v1/chat/stream",
            json={"session_id": "stream-s3", "message": "긴 텍스트 테스트", "response_mode": "text"},
        ) as resp:
            assert resp.status_code == 200
            for idx, _line in enumerate(resp.iter_lines()):
                if idx >= 1:
                    break

        metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert "chat_stream_disconnect_total" in metrics.text
