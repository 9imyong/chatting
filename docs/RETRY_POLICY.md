# Retry Policy

## 목적
retry 동작을 provider spec / error taxonomy / idempotency 기준으로 일관되게 유지한다.

## 기본 원칙
1. `error_code + status_code + exception_type + idempotency`를 함께 판단한다.
2. `invalid body/json`은 재시도하지 않는다.
3. timeout/connect/read를 구분하고, 전체 timeout budget(`HTTP_RETRY_TOTAL_TIMEOUT_SEC`)을 넘기지 않는다.
4. provider별 override(`LLM_HTTP_RETRY_COUNT`, `TTS_HTTP_RETRY_COUNT`)를 지원한다.

## Retry Matrix
| provider | condition | error_code | retry | notes |
|---|---|---|---|---|
| llm | HTTP 429 | `LLM_BAD_RESPONSE` | yes | backoff 적용 |
| llm | HTTP 500/502/503/504 | `LLM_BAD_RESPONSE` | yes | query-like, idempotent=true |
| llm | HTTP 400/401/403/404 | `LLM_BAD_RESPONSE` | no | client/semantic 오류 |
| llm | connect timeout | `LLM_TIMEOUT` | yes | 요청 미도달 가능성 높음 |
| llm | read/total timeout | `LLM_TIMEOUT` | yes | idempotent 호출만 허용 |
| llm | invalid body/json | `LLM_BAD_RESPONSE` | no | 스펙 불일치로 간주 |
| tts | HTTP 429 | `TTS_BAD_RESPONSE` | yes | provider throttling 완화 목적 |
| tts | HTTP 500/502/503/504 | `TTS_BAD_RESPONSE` | conditional | `TTS_SYNTHESIS_IDEMPOTENT=true` 일 때만 |
| tts | HTTP 400/401/403/404 | `TTS_BAD_RESPONSE` | no | 요청 오류 |
| tts | connect timeout | `TTS_TIMEOUT` | yes | 요청 미도달 가능성 높음 |
| tts | read/total timeout | `TTS_TIMEOUT` | conditional | `TTS_SYNTHESIS_IDEMPOTENT=true` 일 때만 |
| tts | invalid body/json | `TTS_BAD_RESPONSE` | no | semantic 실패 |

## 설정
- `HTTP_RETRY_COUNT`: 공통 재시도 횟수(추가 시도 횟수)
- `LLM_HTTP_RETRY_COUNT`, `TTS_HTTP_RETRY_COUNT`: provider별 override (`-1`이면 공통값 사용)
- `HTTP_RETRY_BASE_DELAY_SEC`, `HTTP_RETRY_MAX_DELAY_SEC`
- `HTTP_RETRY_JITTER_ENABLED`, `HTTP_RETRY_JITTER_RATIO`
- `HTTP_RETRY_TOTAL_TIMEOUT_SEC`: 전체 retry budget 상한
- `TTS_SYNTHESIS_IDEMPOTENT`: TTS 멱등성 가정 여부

## 운영 리스크
1. retry가 길어지면 API 지연과 downstream 부하가 증가한다.
2. 멱등성 가정이 실제와 다르면 중복 생성 위험이 있다.
3. 과도한 정책 복잡도는 장애 분석 난이도를 높인다.
