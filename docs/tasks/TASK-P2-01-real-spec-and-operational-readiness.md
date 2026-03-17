# TASK-P2-01-real-spec-and-operational-readiness

## 상태
- STATUS: DONE
- 실행 순서: P2-1

## 1. 개요
- 목적: retry 정책 선행조건인 real provider spec / readiness 구조 / error contract를 먼저 확정
- 범위: P2
- 배경: 실제 동작 기준이 정해지지 않은 상태에서 retry 세분화 시 정책 불일치 위험이 큼

## 2. 선행 완료 목표
1. real provider API spec 확정 (vLLM / GPT-SoVITS)
2. readiness dependency 상태 구조 확정
3. 공통 error contract 및 error_code taxonomy 정의

## 3. 컨벤션 체크리스트
- [x] 계층 분리(api/application/domain/adapters) 준수
- [x] 설정 env 관리 준수 (`env/.env.example` 반영)
- [x] health/ready/metrics 영향 확인
- [x] 예외 처리/에러 응답 형식 점검
- [x] request_id/trace_id 로깅/응답 연계 점검
- [x] 테스트 추가 또는 영향 분석 기록

## 4. 작업 내용(초안)
1. vLLM/GPT-SoVITS 실제 요청/응답 계약 문서화 및 adapter 매핑 확정
2. `/ready` 응답 스키마 및 dependency 상태 표현(up/down, 원인) 확정
3. 공통 error response 스키마와 `error_code taxonomy` 확정
4. provider별 실패 케이스(4xx/5xx/timeout/invalid body) 표준 매핑
5. API_SPEC 및 CONVENTION/RUNBOOK 연동 업데이트

## 5. 예상 산출물
- `app/adapters/outbound/vllm_http_client.py`
- `app/adapters/outbound/gptsovits_http_client.py`
- `app/api/routes/health.py`
- `app/domain/exceptions/errors.py`
- `docs/API_SPEC.md`
- `docs/RUNBOOK.md`

## 6. 검증 계획
- 실제 provider 연동 smoke/integration 테스트
- `/ready` 정상/부분장애/전체장애 응답 검증
- error_code 표준 케이스별 응답 검증

## 7. 리스크/이슈
- provider 버전 차이로 스펙 드리프트 가능
- 운영 환경별 readiness 기준 차이 가능

## 8. 다음 단계 TODO
1. STEP 2 retry tuning 태스크로 정책 세분화 이관
2. contract test를 CI에 포함

## 9. 검증 결과
- 실행 명령: `PYTHONPYCACHEPREFIX=.pycache_tmp python3 -m pytest -q`
- 결과: `12 passed`
