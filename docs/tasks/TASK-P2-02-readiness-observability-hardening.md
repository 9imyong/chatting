# TASK-P2-02-readiness-observability-hardening

## 상태
- STATUS: DONE
- 실행 순서: P2-2

## 선행조건 (필수)
1. `TASK-P2-01-real-spec-and-operational-readiness` 완료

## 1. 개요
- 목적: readiness/metrics/logging 운영 진단력 강화
- 범위: P2
- 배경: 장애 원인 파악 속도를 높이기 위한 관측성 보강 필요

## 2. 컨벤션 체크리스트
- [x] 계층 분리(api/application/domain/adapters) 준수
- [x] 설정 env 관리 준수 (`env/.env.example` 반영)
- [x] health/ready/metrics 영향 확인
- [x] 예외 처리/에러 응답 형식 점검
- [x] request_id/trace_id 로깅/응답 연계 점검
- [x] 테스트 추가 또는 영향 분석 기록

## 3. 작업 내용(초안)
1. `/ready`에 dependency 상태 + 최근 성공 시각/지연 포함
2. inference/tts 단계별 latency metric 추가
3. 구조화 로그 필드 표준(request_id, trace_id, session_id, provider)
4. 기본 dashboard/alert 규칙 초안 작성

## 4. 예상 산출물
- `app/api/routes/health.py`
- `app/common/metrics/metrics.py`
- `app/common/logging/logger.py`
- `docs/RUNBOOK.md` 일부 확장

## 5. 검증 계획
- 의존성 down/up 시 readiness 응답 값 검증
- 메트릭 노출 확인 및 라벨 값 점검

## 6. 리스크/이슈
- 라벨 폭발(고카디널리티) 위험
- 과도한 로그량 증가 가능성

## 7. 다음 단계 TODO
1. 알람 임계값 운영 환경 튜닝
2. 트레이싱(OTel) 연결

## 8. 검증 결과
- 실행 명령: `PYTHONPYCACHEPREFIX=.pycache_tmp python3 -m pytest -q`
- 결과: `13 passed`
