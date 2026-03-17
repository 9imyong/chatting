# Task Workflow

## 목적
작업 단위(Task)마다 컨벤션 준수 여부를 점검하고, 변경 이력을 문서로 남긴다.

## 운영 규칙
1. 모든 개발 작업은 Task ID를 먼저 발급한다.
2. 코드를 수정하기 전, 컨벤션 체크리스트를 작성한다.
3. 구현 후 테스트/검증 결과를 기록한다.
4. 후속 TODO를 Task 문서에 남긴다.
5. PR/커밋 메시지에 Task ID를 포함한다.

## Task 파일 규칙
- 경로: `docs/tasks/`
- 파일명: `TASK-P<phase>-<order>-<slug>.md`
- 예시: `TASK-P0-01-bootstrap.md`

## 최소 체크리스트
1. 계층 분리(api/application/domain/adapters) 준수
2. 설정값 env 관리 준수 (`env/.env.example` 반영)
3. health/ready/metrics 영향 여부 확인
4. 예외 처리/에러 응답 형식 일관성 확인
5. 로그에 request_id/trace_id 연계 확인
6. 테스트(최소 unit/integration) 추가 또는 영향 분석

## Definition of Done
1. 컨벤션 체크리스트 완료
2. 코드 변경 요약 작성
3. 검증 결과(테스트/수동 점검) 기록
4. 리스크 및 다음 TODO 기록
