# 모델 서빙 프로젝트 컨벤션 (Final)

## 1. 목적
이 문서는 모델 서빙 프로젝트의 **개발/운영 표준**을 정의한다.  
목표는 구조 일관성, 운영 복잡도 감소, 장애 대응 가능성, 팀 협업 생산성 확보다.

## 2. 적용 범위
다음 프로젝트에 공통 적용한다.

1. OCR 서빙
2. Vision Detection/Classification/Segmentation 서빙
3. TTS/STT/LLM 추론 API
4. FastAPI 기반 동기/비동기 서빙
5. Kafka/Redis/DB 연동 비동기 추론 시스템

## 3. 핵심 원칙

1. 운영 우선: 정확도뿐 아니라 안정성/재현성/관측성을 동등하게 본다.
2. 책임 분리: API, Application, Domain, Infra, Runtime 역할을 섞지 않는다.
3. 관측 가능성: request_id/trace_id, latency, 실패 원인을 반드시 남긴다.
4. 동시성 명시: semaphore/worker/batch/queue 상한을 설정값으로 관리한다.

## 4. 권장 아키텍처

1. 동기형: `Client -> FastAPI -> Model Runtime -> Response`
2. 비동기형: `Client -> API -> Queue -> Worker -> Storage/Callback`
3. 혼합형: `Submit API -> Job 저장 -> Queue -> Worker -> Result 저장 -> Status API`

## 5. 표준 디렉토리
```text
project/
├─ app/
│  ├─ api/{routes,deps,schemas}
│  ├─ application/{commands,queries,services,dto}
│  ├─ domain/{models,policies,entities,exceptions}
│  ├─ ports/{inbound,outbound}
│  ├─ adapters/{inbound,outbound}
│  ├─ runtime/{model_manager,inference,batching}
│  ├─ workers/
│  ├─ infra/{kafka,redis,db,storage}
│  ├─ common/{logging,metrics,tracing,config,utils}
│  └─ main.py
├─ tests/{unit,integration,e2e}
├─ deploy/{docker,compose,k8s}
├─ docs/{README.md,ARCHITECTURE.md,CONVENTION.md,RUNBOOK.md,API_SPEC.md}
├─ scripts/
├─ env/
│  ├─ .env.example
│  ├─ .env.dev
│  ├─ .env.staging
│  └─ .env.prod
├─ pyproject.toml
└─ Makefile
```

## 6. 네이밍 규칙

1. 파일명: 소문자 snake_case, 의미 없는 `utils.py/service.py/manager.py` 남용 금지
2. 클래스명: PascalCase, 역할 명확히 표현
3. 함수명: 동사 시작, 행위/반환 의도 명확히 표현

## 7. API 규칙

1. 엔드포인트: 버전 prefix 필수 (`/api/v1/...`)
2. 운영 엔드포인트 분리: `/health`, `/ready`, `/metrics`
3. 요청/응답: Pydantic schema 필수
4. 에러: 내부 예외 원문 직접 노출 금지
5. 공통 응답 필드: `status`, `message`, `request_id`, `data`

성공 예시:
```json
{
  "status": "success",
  "message": "inference completed",
  "request_id": "req-1234",
  "data": {}
}
```

실패 예시:
```json
{
  "status": "error",
  "message": "invalid input",
  "request_id": "req-1234",
  "error_code": "INVALID_ARGUMENT"
}
```

## 8. 모델 로딩/추론 규칙

1. 모델은 프로세스 시작 시점 또는 명시적 lazy init 시 1회 로드
2. 요청마다 모델 로드 금지
3. 모델 접근은 Model Manager 단일 경유
4. 추론 파이프라인 분리: `validate -> preprocess -> infer -> postprocess -> serialize`
5. 모델 경로/버전/디바이스/배치/동시성은 환경설정으로 외부화

## 9. 동시성/배치/자원 규칙

1. GPU 모델 무제한 동시 요청 금지
2. semaphore/lock/worker 수 명시
3. batch size/timeout 하드코딩 금지
4. partial failure 처리 전략 필수
5. 최소 외부화 변수:
   - `MODEL_NAME`
   - `MODEL_VERSION`
   - `DEVICE`
   - `MAX_CONCURRENCY`
   - `BATCH_SIZE`
   - `BATCH_TIMEOUT_MS`
   - `REQUEST_TIMEOUT_SEC`
   - `QUEUE_TOPIC`

## 10. Queue/메시징 규칙

1. Redis: 캐시/락/멱등성 키/상태 저장
2. Kafka: 비동기 작업 큐/재처리 가능한 이벤트
3. envelope 스키마 필수:
```json
{
  "event_type": "ocr.requested",
  "event_version": "v1",
  "request_id": "req-1234",
  "timestamp": "2026-03-17T09:00:00Z",
  "payload": {}
}
```
4. 멱등성: `request_id` 또는 `job_id` 기반 중복 방지
5. 실패 처리: retry 정책, DLQ 사용 여부, 원인 코드 저장 필수

## 11. 설정 관리

1. 설정은 코드 하드코딩 금지, `env/` 폴더의 환경변수 파일로 관리
2. `env/.env.example` 최신 유지
3. 민감정보 커밋 금지
4. Pydantic Settings 등으로 타입 검증
5. 기본/필수값 구분

## 12. 로깅/메트릭/트레이싱

1. `print` 금지, 구조화 로그 사용
2. 로그 필드: `request_id`, `job_id`, `trace_id`
3. 민감정보/원본 대용량 payload 로그 금지
4. 필수 메트릭:
   - request/success/failure count
   - latency(p50/p95/p99)
   - in-progress request
   - queue depth/kafka lag
   - batch size distribution
   - GPU util/memory
   - worker restart count
5. 필수 트레이싱 포인트:
   - ingress, validation, publish, consume
   - preprocess, inference, postprocess, storage write

## 13. 예외 처리

1. 분류: Client/Business/Infra/Runtime
2. broad except 남용 금지
3. 커스텀 예외로 의미 있게 래핑
4. 사용자 응답과 내부 장애 로그 분리

## 14. 테스트 기준

1. Unit/Integration/E2E 분리
2. 최소 기준:
   - 주요 정상 흐름 1개 이상
   - 대표 실패 케이스 1개 이상
   - 모델 로딩/추론 smoke test
   - health/ready endpoint test
3. 배포 전:
   - 설정 누락 점검
   - 모델 파일 접근성
   - Queue/DB 연결성
   - readiness 통과

## 15. 배포/운영

1. Docker 멀티스테이지 빌드 권장
2. non-root 실행 권장
3. liveness/readiness 분리
4. resource request/limit 명시
5. config/secret 분리
6. 문서 필수:
   - README
   - ARCHITECTURE
   - CONVENTION
   - RUNBOOK
   - API_SPEC

## 16. Git/브랜치/커밋

1. 브랜치:
   - `main`, `develop`
   - `feature/*`, `fix/*`, `refactor/*`, `docs/*`, `chore/*`, `test/*`
2. 커밋 형식: `type(scope): 요약`
3. type: `feat/fix/refactor/docs/test/chore/perf/style/ci/build`
4. scope 예: `api`, `worker`, `runtime`, `kafka`, `redis`, `db`, `storage`, `config`, `deploy`
5. 금지 메시지: `fix: 수정`, `update`, `final`, `작업중` 등 의미 없는 제목

## 17. 문서화 기준

1. README: 목적, 구조, 실행법, env, 주요 API, 배포법
2. ARCHITECTURE: 요청 흐름, 컴포넌트 역할, 병목, 장애 대응 포인트
3. RUNBOOK: 증상, 확인지표, 원인후보, 즉시조치, 복구절차, 후속조치

## 18. 프로젝트 시작 체크리스트

### 18.1 초기 설계
1. 동기/비동기/혼합형 중 아키텍처 선택
2. 처리량/지연 목표(SLO) 정의
3. 모델 로딩/워밍업 전략 확정
4. 장애 시나리오와 복구 책임자 정의

### 18.2 구현 전
1. 표준 디렉토리 생성
2. 설정 스키마 및 `env/.env.example` 작성
3. 공통 응답/에러 스키마 정의
4. 로깅/메트릭/헬스체크 기본 탑재
5. Queue 메시지 envelope 스키마 확정

### 18.3 배포 전
1. readiness/liveness 통과 확인
2. 모델 파일 접근/디바이스 할당 검증
3. Queue/DB/Storage 연결 검증
4. 주요 정상/실패 E2E 실행
5. RUNBOOK 및 대시보드 링크 점검

## 19. Task 단위 작업 규칙

1. 모든 변경 작업은 Task 문서(`docs/tasks/TASK-YYYYMMDD-<slug>.md`)를 생성하거나 갱신한다.
2. Task 문서에는 최소한 아래를 포함한다.
   - 컨벤션 체크리스트
   - 작업 내용 요약
   - 변경 파일 목록
   - 검증 결과(테스트/수동 확인)
   - 리스크와 후속 TODO
3. 구현 전/구현 후 각각 컨벤션 체크 항목을 점검한다.
4. PR/커밋 메시지에 Task ID를 포함해 추적 가능하게 유지한다.
5. 상세 운영 방식은 `docs/TASK_WORKFLOW.md`를 따른다.

## 20. 권장 선언문
본 프로젝트는 모델 정확도뿐 아니라 운영 안정성, 재현 가능성, 관측 가능성을 동일한 수준으로 중요하게 다룬다. 모든 구현은 요청 처리, 모델 자원 관리, 장애 대응, 확장 가능성을 기준으로 검토한다.

## 21. 최종 원칙
모든 프로젝트는 아래 질문에 답할 수 있어야 한다.

1. 이 모델은 언제 로드되는가?
2. 동시에 몇 개까지 처리 가능한가?
3. 실패하면 어디서 보이는가?
4. 재처리는 가능한가?
5. 장애 시 누가 무엇을 보고 어떻게 복구하는가?
6. 새 프로젝트가 와도 같은 방식으로 확장 가능한가?
