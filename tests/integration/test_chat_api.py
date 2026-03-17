from fastapi.testclient import TestClient

from app.main import app


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
