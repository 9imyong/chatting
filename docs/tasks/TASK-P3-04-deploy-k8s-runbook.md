# TASK-P3-04-deploy-k8s-runbook

## 상태
- STATUS: BACKLOG
- 실행 순서: P3-4


## 1. 개요
- 목적: Kubernetes 배포 표준화 및 운영 런북 강화
- 범위: P3
- 배경: 운영 전환을 위한 배포/복구 절차 표준 필요

## 2. 컨벤션 체크리스트
- [ ] 계층 분리(api/application/domain/adapters) 준수
- [ ] 설정 env 관리 준수 (`env/.env.example` 반영)
- [ ] health/ready/metrics 영향 확인
- [ ] 예외 처리/에러 응답 형식 점검
- [ ] request_id/trace_id 로깅/응답 연계 점검
- [ ] 테스트 추가 또는 영향 분석 기록

## 3. 작업 내용(초안)
1. k8s 매니페스트/helm 템플릿 추가
2. liveness/readiness/resource 정책 반영
3. secret/config 분리 및 배포 파이프라인 정리
4. 장애 대응 runbook 시나리오 구체화

## 4. 예상 산출물
- `deploy/k8s/*`
- `docs/RUNBOOK.md`
- `docs/ARCHITECTURE.md` 업데이트

## 5. 검증 계획
- 롤링 업데이트/롤백 테스트
- readiness 실패 시 트래픽 차단 검증

## 6. 리스크/이슈
- 환경별 설정 drift
- 배포 자동화 권한/보안 이슈

## 7. 다음 단계 TODO
1. canary 전략 추가
2. 운영 대시보드 링크/알람 핸들러 문서화
