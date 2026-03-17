# Chat Model Serving Backend (P0)

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

## Docker Compose
```bash
docker compose -f docker-compose.dev.yml up
```

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

## 테스트
```bash
pytest -q
```

## Task 운영
- 작업 단위 문서화 규칙: [docs/TASK_WORKFLOW.md](/Users/9imyong/workspace/chatting/docs/TASK_WORKFLOW.md)
- Task 템플릿: [docs/tasks/TASK_TEMPLATE.md](/Users/9imyong/workspace/chatting/docs/tasks/TASK_TEMPLATE.md)
- 최근 작업 기록(P0): [docs/tasks/TASK-20260317-chat-p0-bootstrap.md](/Users/9imyong/workspace/chatting/docs/tasks/TASK-20260317-chat-p0-bootstrap.md)
- 최근 작업 기록(P1): [docs/tasks/TASK-20260317-chat-p1-lifespan-and-real-adapters.md](/Users/9imyong/workspace/chatting/docs/tasks/TASK-20260317-chat-p1-lifespan-and-real-adapters.md)
