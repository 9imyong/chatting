# TASK-P3-02-streaming-response

## 상태
- STATUS: DONE
- 실행 순서: P3-2


## 1. 개요
- 목적: 텍스트 스트리밍 응답 지원(SSE)
- 범위: P3
- 배경: 실시간 대화 UX 개선 요구

## 2. 컨벤션 체크리스트
- [x] 계층 분리(api/application/domain/adapters) 준수
- [x] 설정 env 관리 준수 (`env/.env.example` 반영)
- [x] health/ready/metrics 영향 확인
- [x] 예외 처리/에러 응답 형식 점검
- [x] request_id/trace_id 로깅/응답 연계 점검
- [x] 테스트 추가 또는 영향 분석 기록

## 3. 작업 내용(초안)
1. SSE(`text/event-stream`) 프로토콜 고정 및 `/api/v1/chat/stream` 추가
2. chunk 단위 생성/전송 경로 구현
3. cancel/timeout/backpressure 처리
4. 클라이언트 재연결 정책 정의

## 4. 예상 산출물
- 스트리밍 라우터/스키마
- 스트리밍 runbook 항목
- 부하 테스트 시나리오

## 5. 검증 결과
1. `/api/v1/chat/stream` SSE 이벤트(`start/token/done/error`) 검증
2. provider 장애 시 `event:error` 검증
3. disconnect 시 metrics 반영 검증
4. 전체 pytest 통과

## 6. 검증 계획
- 스트리밍 정상/중단/재연결 케이스 검증
- 고동시성 스트리밍 안정성 점검

## 7. 리스크/이슈
- 연결 수 증가로 리소스 압박
- 프록시/로드밸런서 idle timeout 영향

## 8. 다음 단계 TODO
1. 오디오 chunk 포맷 최적화
2. 스트리밍 QoS 지표 추가
