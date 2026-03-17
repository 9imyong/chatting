# Task Execution Order

## 목적
P0/P1/P2/P3 태스크가 섞여 보이지 않도록 전체 실행 순서를 단일 문서에서 관리한다.

## 전체 순서
1. `P0-1` 완료: `TASK-P0-01-bootstrap` (DONE)
2. `P1-1` 완료: `TASK-P1-01-lifespan-and-real-adapters` (DONE)
3. `P2-1` 완료: `TASK-P2-01-real-spec-and-operational-readiness` (DONE)
4. `P2-2` 완료: `TASK-P2-02-readiness-observability-hardening` (DONE)
5. `P2-3` 완료: `TASK-P2-03-postgres-session-store` (DONE)
6. `P2-4` 완료: `TASK-P2-04-error-policy-retry-tuning` (DONE)
7. `P3-1` 대기: `TASK-P3-01-kafka-async-chat-pipeline` (BACKLOG)
8. `P3-2` 완료: `TASK-P3-02-streaming-response` (DONE)
9. `P3-3` 대기: `TASK-P3-03-auth-rate-limit-multitenancy` (BACKLOG)
10. `P3-4` 대기: `TASK-P3-04-deploy-k8s-runbook` (BACKLOG)
11. `P3-5` 대기: `TASK-P3-05-load-failover-validation` (BACKLOG)

## P2 세부 원칙
1. `P2-1` 완료 전 `P2-2 ~ P2-4` 착수 금지
2. `P2-4(retry tuning)`은 다음 선행조건 충족 후 착수
   - real provider API spec 확정
   - readiness dependency 상태 구조 확정
   - 공통 error contract / error_code taxonomy 확정

## 상태 정의
- `DONE`: 완료 및 검증 종료
- `READY`: 즉시 착수 가능
- `BACKLOG`: 선행조건 또는 우선순위로 대기
- `MERGED`: 다른 태스크로 통합됨
