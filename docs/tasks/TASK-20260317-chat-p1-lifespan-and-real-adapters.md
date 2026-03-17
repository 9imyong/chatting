# TASK-20260317-chat-p1-lifespan-and-real-adapters

## 1. 개요
- 목적: P0 스캐폴딩 이후 실제 운영 가능한 P1 구조로 전환
- 요청자/배경: stub 기반 FastAPI 프로젝트를 실제 vLLM / GPT-SoVITS 연동 가능 상태로 고도화
- 범위(P0/P1/...): P1

## 2. 컨벤션 체크리스트
- [x] 계층 분리(api/application/domain/adapters) 준수
- [x] 설정 env 관리 준수 (`env/.env.example` 반영)
- [x] health/ready/metrics 영향 확인
- [x] 예외 처리/에러 응답 형식 점검
- [x] request_id/trace_id 로깅/응답 연계 점검
- [x] 테스트 추가 또는 영향 분석 기록

## 3. 작업 내용
1. FastAPI startup/shutdown `on_event` 제거 후 lifespan 기반으로 전환
2. bootstrap wiring(`app/bootstrap.py`) 추가로 adapter/repository/service 주입 구조 정리
3. vLLM HTTP adapter(`vllm_http_client.py`) 및 GPT-SoVITS HTTP adapter(`gptsovits_http_client.py`) 추가
4. env 기반 provider 선택(`LLM_PROVIDER`, `TTS_PROVIDER`, `SESSION_BACKEND`) 적용
5. Redis repository에 `set_history` 추가 및 TTL/에러 처리 보강
6. `/ready` 응답을 dependency 상태 기반 상세 구조로 강화 (장애 시 503)
7. retry/timeout/backoff+jitter 정책 유틸 추가
8. history builder 분리 및 최근 N turn 유지 정책 반영
9. 단위/통합 테스트 확장

## 4. 변경 파일
- `app/main.py`
- `app/bootstrap.py`
- `app/common/config/settings.py`
- `app/common/utils/retry.py`
- `app/ports/outbound/llm_client.py`
- `app/ports/outbound/tts_client.py`
- `app/ports/outbound/session_repository.py`
- `app/adapters/outbound/vllm_client_stub.py`
- `app/adapters/outbound/gptsovits_client_stub.py`
- `app/adapters/outbound/vllm_http_client.py`
- `app/adapters/outbound/gptsovits_http_client.py`
- `app/adapters/outbound/inmemory_session_repository.py`
- `app/adapters/outbound/redis_session_repository.py`
- `app/application/services/chat_orchestration_service.py`
- `app/application/services/history_builder.py`
- `app/api/deps/providers.py`
- `app/api/routes/chat.py`
- `app/api/routes/health.py`
- `app/api/schemas/chat.py`
- `env/.env.example`
- `tests/unit/test_chat_service.py`
- `tests/unit/test_bootstrap_wiring.py`
- `tests/integration/test_health_ready_metrics.py`

## 5. 검증 결과
- 실행 명령: `PYTHONPYCACHEPREFIX=.pycache_tmp python3 -m pytest -q`
- 결과: `7 passed`
- 비고: lifespan 전환으로 `on_event` deprecation warning 해소

## 6. 리스크/이슈
- vLLM/GPT-SoVITS 실제 API 필드 스펙 차이가 있을 수 있어 운영 환경에서 endpoint/payload 조정 필요
- 현재 retry 대상은 HTTP timeout/network/status 중심이며, 세부 status code 별 정책은 추가 여지 있음

## 7. 다음 단계 TODO
1. real adapter payload를 실제 배포 스펙에 맞게 확정 (필드명/응답 스키마)
2. readiness에 latency 또는 마지막 성공 시간 등 운영 지표 확장
3. Postgres 저장소 adapter 추가(P2)
4. Kafka async 처리 경로 분리(P2)
