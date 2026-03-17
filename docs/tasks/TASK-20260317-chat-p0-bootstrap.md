# TASK-20260317-chat-p0-bootstrap

## 1. 개요
- 목적: vLLM + GPT-SoVITS 기반 FastAPI 백엔드 P0 스캐폴딩 구현
- 요청자/배경: 모델 서빙 프로젝트 초기 구축
- 범위(P0/P1/...): P0

## 2. 컨벤션 체크리스트
- [x] 계층 분리(api/application/domain/adapters) 준수
- [x] 설정 env 관리 준수 (`env/.env.example` 반영)
- [x] health/ready/metrics 영향 확인
- [x] 예외 처리/에러 응답 형식 점검
- [x] request_id/trace_id 로깅/응답 연계 점검
- [x] 테스트 추가 또는 영향 분석 기록

## 3. 작업 내용
1. FastAPI 앱 구조 및 계층형 디렉토리 생성
2. `/health`, `/ready`, `/metrics`, `/api/v1/chat` 구현
3. vLLM/GPT-SoVITS stub adapter, Redis/InMemory session repository 구현
4. Chat orchestration service 및 스키마/예외 처리 구현
5. README, env 예시, compose 파일 작성
6. 테스트 코드 4개 작성 및 통과 확인

## 4. 변경 파일
- `app/main.py`
- `app/api/routes/chat.py`
- `app/api/routes/health.py`
- `app/application/services/chat_orchestration_service.py`
- `app/adapters/outbound/*`
- `app/ports/outbound/*`
- `app/common/*`
- `app/domain/*`
- `tests/unit/test_chat_service.py`
- `tests/integration/test_chat_api.py`
- `tests/integration/test_health_ready_metrics.py`
- `README.md`
- `env/.env.example`
- `docker-compose.dev.yml`

## 5. 검증 결과
- 실행 명령: `PYTHONPYCACHEPREFIX=.pycache_tmp python3 -m pytest -q`
- 결과: `4 passed`
- 비고: FastAPI `on_event` deprecation warning 존재

## 6. 리스크/이슈
- 현재 실행 환경 Python 3.9 기반이어서 일부 타입 표기 호환 조정 필요했음
- startup/shutdown 이벤트를 lifespan으로 마이그레이션 필요

## 7. 다음 단계 TODO
1. FastAPI lifespan 전환
2. 실제 vLLM/GPT-SoVITS API 스펙 매핑
3. PostgreSQL 저장소 adapter 추가
4. retry 정책(backoff/jitter) 고도화
