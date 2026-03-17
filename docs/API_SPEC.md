# API Specification

## POST /api/v1/chat

### Auth Header
- `Authorization: Bearer <tenant_api_key>` (when `AUTH_ENABLED=true`)

### Request
```json
{
  "session_id": "session-001",
  "message": "안녕",
  "response_mode": "text | text_audio",
  "voice_id": "optional",
  "speaker": "optional",
  "language": "optional",
  "reference_audio_url": "optional"
}
```

## POST /api/v1/chat/stream

### Auth Header
- `Authorization: Bearer <tenant_api_key>` (when `AUTH_ENABLED=true`)

### Request
```json
{
  "session_id": "session-001",
  "message": "안녕",
  "response_mode": "text"
}
```

### Response
- `Content-Type: text/event-stream`
- SSE event 순서: `start` -> `token`(0..N) -> `done`
- 실패 시: `start` -> `error`

### SSE Event Examples
```text
event: start
data: {"request_id":"req-...","trace_id":"trace-...","session_id":"session-001"}

event: token
data: {"delta":"안녕","sequence":1}

event: done
data: {"finish_reason":"stop","usage":null}
```

```text
event: error
data: {"error":{"code":"LLM_TIMEOUT","message":"llm provider read timeout"}}
```

### Streaming Policy
1. 1차 구현은 text streaming만 지원한다 (`response_mode=text`).
2. 재연결은 새 요청으로 처리한다(중간 이어받기 미지원).
3. server-side resumable stream은 현재 범위에서 지원하지 않는다.
4. 인증/tenant rate limit 정책은 `/api/v1/chat`과 동일하게 적용된다.

### Success Response
```json
{
  "status": "success",
  "message": "chat completed",
  "request_id": "req-...",
  "trace_id": "trace-...",
  "data": {
    "text": "generated text",
    "audio_url": "optional",
    "response_mode": "text | text_audio"
  }
}
```

### Error Response (Common Contract)
```json
{
  "error": {
    "code": "LLM_TIMEOUT",
    "message": "human readable message",
    "request_id": "req-...",
    "trace_id": "trace-..."
  }
}
```

## GET /ready

### Response
```json
{
  "status": "ok | degraded | fail",
  "dependencies": {
    "llm": {
      "status": "ok | fail",
      "latency_ms": 12.3,
      "last_success_ts": "2026-03-17T11:00:00+00:00",
      "reason": null
    },
    "tts": {
      "status": "ok | fail",
      "latency_ms": 20.1,
      "last_success_ts": "2026-03-17T11:00:01+00:00",
      "reason": null
    },
    "session_store": {
      "status": "ok | fail",
      "latency_ms": 3.2,
      "reason": null
    }
  }
}
```

### Status Policy
1. all dependency ok -> HTTP 200, `status=ok`
2. partial failure -> HTTP 200, `status=degraded`
3. all dependency fail or bootstrap incomplete -> HTTP 503, `status=fail`

## Error Code Taxonomy
- `LLM_TIMEOUT`
- `LLM_BAD_RESPONSE`
- `TTS_TIMEOUT`
- `TTS_BAD_RESPONSE`
- `SESSION_STORE_ERROR`
- `INTERNAL_ERROR`
- `INVALID_ARGUMENT`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `RATE_LIMIT_EXCEEDED`

## Session Backend Notes
- `SESSION_BACKEND`는 `memory | redis | postgres`를 지원한다.
- `postgres` backend는 `expires_at` 기반 `expiration/cleanup strategy`를 사용한다.
