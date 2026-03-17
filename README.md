# Chat Model Serving Backend

vLLM 기반 텍스트 생성과 GPT-SoVITS 기반 음성 합성을 결합한 FastAPI 백엔드의 최소 동작 버전입니다.

## 목적
- `/api/v1/chat` 단일 엔드포인트로 텍스트/음성 응답 지원
- 세션별 대화 히스토리 관리
- `/health`, `/ready`, `/metrics` 운영 엔드포인트 제공
- 외부 서비스 장애 시 명확한 예외 응답 제공

## 디렉토리 요약
- `app/api`: 요청/응답 스키마와 라우터
- `app/application`: 유스케이스 오케스트레이션
- `app/domain`: 도메인 엔티티/예외
- `app/ports`: 외부 의존 포트 인터페이스
- `app/adapters`: vLLM/GPT-SoVITS/Redis 등 외부 연동 구현
- `app/common`: 설정/로깅/메트릭/트레이싱
- `tests`: unit/integration 테스트
- `env`: 환경변수 파일

## 실행
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp env/.env.example env/.env.dev
uvicorn app.main:app --reload --port 8000
```

## Session Backend 선택
- `SESSION_BACKEND=memory`: 개발/테스트 기본값
- `SESSION_BACKEND=redis`: 빠른 임시 저장, TTL 기반 세션
- `SESSION_BACKEND=postgres`: 내구성 저장, `expiration/cleanup strategy` 기반 세션

PostgreSQL backend 사용 예시:
```bash
export SESSION_BACKEND=postgres
export POSTGRES_DSN=postgresql://app:app@localhost:5432/app
```

마이그레이션 SQL 적용 예시:
```bash
psql "$POSTGRES_DSN" -f deploy/migrations/0001_create_chat_session_tables.sql
```

## Docker Compose
```bash
docker compose -f docker-compose.dev.yml up
```

## 실서버(vLLM + GPT-SoVITS) 스택 기동
실모델 기반 서버가 필요한 경우:
```bash
cp env/.env.real.example env/.env.real
# env/.env.real의 모델/이미지/경로 값 수정
ENV_FILE=env/.env.real bash scripts/run_real_stack.sh
bash scripts/smoke_real_stack.sh
```

주의:
1. vLLM은 GPU 런타임이 필요합니다.
2. GPT-SoVITS 이미지/실행 명령은 운영 환경에 맞춰 `GPT_SOVITS_IMAGE`를 조정해야 합니다.

## 외부 서버가 없을 때 연동 스모크
실제 vLLM/GPT-SoVITS 서버가 없는 환경에서는 mock provider를 띄워
`real adapter 경로`를 검증할 수 있습니다.

```bash
bash scripts/smoke_with_mock_providers.sh
```

이 스크립트는 아래를 순서대로 실행합니다.
1. vLLM mock 서버 기동 (`/health`, `/v1/chat/completions`)
2. GPT-SoVITS mock 서버 기동 (`/health`, `/synthesize`)
3. API를 `LLM_PROVIDER=vllm`, `TTS_PROVIDER=gptsovits` 모드로 기동
4. `/ready`, `/api/v1/chat`, `/api/v1/chat/stream`, `/metrics` 스모크 호출

## API 예시

### Request (text only)
```json
{
  "session_id": "session-001",
  "message": "안녕, 오늘 일정 추천해줘",
  "response_mode": "text"
}
```

### Request (text + audio)
```json
{
  "session_id": "session-001",
  "message": "이 문장을 읽어줘",
  "response_mode": "text_audio",
  "voice_id": "ko_female_1"
}
```

### Response (text)
```json
{
  "status": "success",
  "message": "chat completed",
  "request_id": "req-123",
  "trace_id": "trace-123",
  "data": {
    "text": "stub-vllm-reply: 안녕, 오늘 일정 추천해줘",
    "audio_url": null,
    "response_mode": "text"
  }
}
```

### Response (text+audio)
```json
{
  "status": "success",
  "message": "chat completed",
  "request_id": "req-124",
  "trace_id": "trace-124",
  "data": {
    "text": "stub-vllm-reply: 이 문장을 읽어줘",
    "audio_url": "https://audio.local/ko_female_1/stub-vllm-reply:_이_문장을_읽어줘.wav",
    "response_mode": "text_audio"
  }
}
```

### Streaming (SSE)
```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"session_id":"session-001","message":"안녕","response_mode":"text"}'
```

## Auth / Rate Limit (P3-3)
- `AUTH_ENABLED=true`일 때 `Authorization: Bearer <tenant_api_key>` 필요
- `AUTH_TENANT_API_KEYS` 형식: `tenant_a:token_a,tenant_b:token_b`
- tenant별 rate limit 기본값: `RATE_LIMIT_REQUESTS_PER_WINDOW`
- tenant별 override: `RATE_LIMIT_TENANT_OVERRIDES`

## 테스트
```bash
pytest -q
```

## 운영 문서
- API 명세: [docs/API_SPEC.md](/Users/9imyong/workspace/chatting/docs/API_SPEC.md)
- 런북: [docs/RUNBOOK.md](/Users/9imyong/workspace/chatting/docs/RUNBOOK.md)
- Retry 정책: [docs/RETRY_POLICY.md](/Users/9imyong/workspace/chatting/docs/RETRY_POLICY.md)
- Streaming 가이드: [docs/STREAMING.md](/Users/9imyong/workspace/chatting/docs/STREAMING.md)

## Task 운영
- 전체 실행순서: [docs/tasks/EXECUTION_ORDER.md](/Users/9imyong/workspace/chatting/docs/tasks/EXECUTION_ORDER.md)
- 작업 단위 문서화 규칙: [docs/TASK_WORKFLOW.md](/Users/9imyong/workspace/chatting/docs/TASK_WORKFLOW.md)
- Task 템플릿: [docs/tasks/TASK_TEMPLATE.md](/Users/9imyong/workspace/chatting/docs/tasks/TASK_TEMPLATE.md)
- 최근 작업 기록(P0): [docs/tasks/TASK-P0-01-bootstrap.md](/Users/9imyong/workspace/chatting/docs/tasks/TASK-P0-01-bootstrap.md)
- 최근 작업 기록(P1): [docs/tasks/TASK-P1-01-lifespan-and-real-adapters.md](/Users/9imyong/workspace/chatting/docs/tasks/TASK-P1-01-lifespan-and-real-adapters.md)
