# Runbook

## Readiness Status Meaning
1. `ok`: llm/tts/session_store 모두 정상
2. `degraded`: 일부 의존성 실패. 서비스는 부분 기능으로 동작 가능
3. `fail`: 전체 의존성 실패 또는 bootstrap 불완전. 즉시 대응 필요

## Dependency Fail 점검 순서
1. `/ready`의 `dependencies.*.reason` 확인
2. LLM 상태 점검
   - `LLM_TIMEOUT`: 네트워크/timeout 설정 확인
   - `LLM_BAD_RESPONSE`: provider 응답 스펙/상태코드 확인
3. TTS 상태 점검
   - `TTS_TIMEOUT`: 네트워크/timeout 설정 확인
   - `TTS_BAD_RESPONSE`: payload/응답 body 구조 확인
4. Session Store 점검
   - `SESSION_STORE_ERROR`: Redis 연결, 인증, TTL 설정 확인
   - `SESSION_BACKEND=postgres` 인 경우 DSN/연결 가능 여부, migration 적용 여부 확인

## Provider Failure Mapping
1. timeout -> `*_TIMEOUT`
2. 4xx -> `*_BAD_RESPONSE`
3. 5xx -> `*_BAD_RESPONSE`
4. invalid json/body -> `*_BAD_RESPONSE`

## Retry Policy Summary
1. 상세 정책은 [docs/RETRY_POLICY.md](/Users/9imyong/workspace/chatting/docs/RETRY_POLICY.md) 기준을 따른다.
2. `429`는 provider 공통 retry 대상이다.
3. `500/502/503/504`는 idempotent 호출만 retry 허용한다.
4. `400/401/403/404`, invalid body/json은 non-retryable로 즉시 실패 처리한다.
5. timeout은 connect/read/total을 구분하며, `HTTP_RETRY_TOTAL_TIMEOUT_SEC` budget 내에서만 재시도한다.

## Dashboard Draft
1. API Request Overview
   - `app_request_total` by `method/path/status`
   - `app_request_latency_seconds` p50/p95/p99
2. Chat Flow
   - `chat_request_total` by `response_mode/result`
   - `chat_request_latency_seconds` p50/p95/p99
3. Provider Health
   - `provider_latency_seconds` by `provider/operation/result`
   - `/ready` status trend (`ok/degraded/fail`)
4. Readiness Probe
   - `readiness_probe_latency_seconds` by `dependency/result`

## Alert Draft
1. Readiness fail 지속
   - 조건: `/ready`가 `fail` 상태로 3분 이상 지속
2. Provider timeout 급증
   - 조건: `provider_latency_seconds{result="failure"}` 증가율 급등
3. Error rate 급증
   - 조건: 5xx 비율 임계치 초과
4. Latency 증가
   - 조건: chat/api p95 latency가 기준치 이상 지속

## Logging Standard
1. 공통 필드
   - `request_id`, `trace_id`, `session_id(optional)`, `provider`, `path`, `latency_ms`, `result`, `status`
2. 로그 레벨 기준
   - INFO: 정상 흐름(inbound request, provider success)
   - ERROR: 예외/실패(provider timeout, invalid response)
3. 민감정보 제외
   - user text 원문
   - token/audio raw payload
   - authorization header

## Known Risks
1. provider 버전 차이로 API 스펙 드리프트 가능
2. 환경별 readiness 기준 차이 가능
3. label explosion 위험
   - 대응: metrics label은 provider/operation/result/path 정도로 제한
4. 과도한 로그량 증가 가능
   - 대응: debug/info/error 분리 및 payload 미기록
5. 과도한 retry로 지연 증가 및 downstream 부하 가능
   - 대응: total timeout budget, provider별 retry 상한, non-retryable 명시

## Postgres Expiration / Cleanup Strategy
1. `SESSION_BACKEND=postgres`는 Redis TTL semantics를 그대로 모사하지 않는다.
2. `chat_sessions.expires_at`를 기준으로 만료 세션을 판별한다.
3. 조회 시 만료 세션은 읽기 대상에서 제외한다.
4. 자동 삭제 job은 현재 범위에서 제외하며, 운영에서는 주기 cleanup job 도입을 권장한다.
5. `chat_messages`는 `(session_pk, turn_index)` 순서로 저장하며 최근 `MAX_HISTORY_TURNS` 기준 trim 가능 구조를 유지한다.

## Postgres 장애 대응 순서
1. `/ready`에서 `session_store.status`와 `reason` 확인
2. `POSTGRES_DSN` 값과 네트워크 접근성 확인
3. `deploy/migrations/0001_create_chat_session_tables.sql` 적용 여부 확인
4. DB 연결 복구 후 `/ready`가 `ok/degraded`에서 정상 반영되는지 재확인
