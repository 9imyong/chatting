# TASK-P3-01-kafka-async-chat-pipeline

## 상태
- STATUS: BACKLOG
- 실행 순서: P3-1


## 1. 개요
- 목적: 비동기 채팅 처리 파이프라인(Kafka + Worker) 도입
- 범위: P3
- 배경: burst traffic 및 장시간 작업 대응 필요

## 2. 컨벤션 체크리스트
- [ ] 계층 분리(api/application/domain/adapters) 준수
- [ ] 설정 env 관리 준수 (`env/.env.example` 반영)
- [ ] health/ready/metrics 영향 확인
- [ ] 예외 처리/에러 응답 형식 점검
- [ ] request_id/trace_id 로깅/응답 연계 점검
- [ ] 테스트 추가 또는 영향 분석 기록

## 3. 작업 내용(초안)
1. submit/status/result API 분리
2. Kafka publish/consume adapter 구현
3. worker 처리 및 결과 저장소 연계
4. retry/DLQ/멱등성 정책 적용

## 4. 예상 산출물
- `app/workers/*`
- `app/infra/kafka/*` 또는 adapter
- job 상태 스키마/API 문서

## 5. 검증 계획
- 큐 발행/소비 E2E 테스트
- 중복 메시지/재처리 시나리오 검증

## 6. 리스크/이슈
- 순서 보장/중복 처리 복잡도
- 운영 장애 시 복구 절차 필요

## 7. 다음 단계 TODO
1. consumer lag 알람 추가
2. 배치 처리 정책 도입 검토
