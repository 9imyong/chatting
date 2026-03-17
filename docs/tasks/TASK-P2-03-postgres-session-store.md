# TASK-P2-03-postgres-session-store

## 상태
- STATUS: DONE
- 실행 순서: P2-3 (P2-1 완료 후)


## 1. 개요
- 목적: Redis 외 PostgreSQL 세션 저장소 adapter 추가
- 범위: P2
- 배경: 세션 내구성/조회 확장성 확보 필요

## 2. 컨벤션 체크리스트
- [x] 계층 분리(api/application/domain/adapters) 준수
- [x] 설정 env 관리 준수 (`env/.env.example` 반영)
- [x] health/ready/metrics 영향 확인
- [x] 예외 처리/에러 응답 형식 점검
- [x] request_id/trace_id 로깅/응답 연계 점검
- [x] 테스트 추가 또는 영향 분석 기록

## 3. 작업 내용(초안)
1. `SESSION_BACKEND=postgres` 분기 추가
2. session/message 분리 스키마 및 인덱스 설계
3. postgres repository adapter 구현(`get_history`, `set_history`, trim, `ping`)
4. migration SQL 추가 및 expiration/cleanup strategy 문서화

## 4. 예상 산출물
- `app/adapters/outbound/postgres_session_repository.py`
- DB 스키마/마이그레이션 파일
- 설정/README 업데이트
- postgres/readiness/test 보강

## 5. 검증 계획
- 세션 저장/조회/turn trim 검증
- DB 장애 시 readiness 반영 및 예외 처리 검증

## 6. 검증 결과
1. postgres repository 단위 테스트 추가
2. readiness postgres 장애(degraded) 통합 테스트 추가
3. backend wiring 테스트에 postgres 분기 추가
4. 전체 pytest 통과

## 7. 리스크/이슈
- TTL 정책을 RDB에 어떻게 적용할지 결정 필요
- 대화 이력 증가 시 성능/보관 정책 필요

## 8. 다음 단계 TODO
1. archive 정책 정의
2. 세션 조회 API 확장 검토
