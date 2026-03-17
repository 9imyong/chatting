# TASK-P2-04-error-policy-retry-tuning

## 상태
- STATUS: DONE
- 실행 순서: P2-4 (P2-1 완료 후)

## 선행조건 (필수)
1. `TASK-P2-01-real-spec-and-operational-readiness` 완료
2. real provider API spec 확정 완료
3. readiness dependency 상태 구조 확정 완료
4. 공통 error contract 및 error_code taxonomy 확정 완료

## 1. 개요
- 목적: 선행조건 확정 결과를 기반으로 retry 정책 세분화
- 범위: P2
- 배경: 선행 산출물 없이 retry를 먼저 세분화하면 실제 동작과 불일치 가능

## 2. 컨벤션 체크리스트
- [x] 계층 분리(api/application/domain/adapters) 준수
- [x] 설정 env 관리 준수 (`env/.env.example` 반영)
- [x] health/ready/metrics 영향 확인
- [x] 예외 처리/에러 응답 형식 점검
- [x] request_id/trace_id 로깅/응답 연계 점검
- [x] 테스트 추가 또는 영향 분석 기록

## 3. 작업 내용(초안)
1. `error_code taxonomy` 기반 retry 정책 설계
2. provider별 정책 분리 (LLM / TTS)
3. timeout/connect/read 구분 정책 적용
4. idempotency 고려한 retry 허용 범위 정의
5. status code + exception 유형별 retry matrix 확정

## 4. 예상 산출물
- `app/common/utils/retry.py`
- provider adapter별 retry 분기 코드
- retry 정책 문서(매트릭스)
- 테스트 케이스 확장

## 6. 검증 결과
1. taxonomy 기반 retry policy(`RetrySignal`, `RetryPolicy`) 적용
2. provider별 idempotency/timeout/status 분기 반영
3. retry matrix 문서(`docs/RETRY_POLICY.md`) 추가
4. 단위/통합 테스트 통과 (`28 passed`)

## 5. 검증 계획
- 재시도 횟수/백오프/지터 단위 테스트
- provider별 retry 동작 통합 테스트
- idempotency 위반 가능 시나리오 회귀 테스트

## 7. 리스크/이슈
- 과도한 retry로 지연 증가 및 다운스트림 부하 가능
- 정책 복잡도 증가로 운영 난이도 상승 가능

## 8. 다음 단계 TODO
1. circuit breaker 도입 검토
2. 동적 정책(런타임 설정) 적용 검토
