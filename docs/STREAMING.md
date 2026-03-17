# Streaming Guide

## 범위
1. endpoint: `POST /api/v1/chat/stream`
2. protocol: SSE(`text/event-stream`)
3. phase-1에서는 텍스트 스트리밍만 지원한다.

## 이벤트 계약
1. `start`: 요청 메타데이터 전달(`request_id`, `trace_id`, `session_id`)
2. `token`: 텍스트 chunk 전달(`delta`, `sequence`)
3. `done`: 정상 종료(`finish_reason`, `usage`)
4. `error`: 실패 종료(`error.code`, `error.message`)

## Cancel / Disconnect / Timeout
1. 클라이언트 연결 종료 시 generator를 중단하고 자원을 해제한다.
2. disconnect/cancel은 로그와 metrics(`chat_stream_disconnect_total`)로 기록한다.
3. stream timeout은 `STREAM_TOTAL_TIMEOUT_SEC` 기준으로 처리한다.

## Backpressure / Flush Strategy
1. chunk 단위는 `STREAM_CHUNK_SIZE` 기반 고정 분할을 사용한다.
2. 지나치게 작은 chunk 남발을 피하기 위해 기본값은 보수적으로 유지한다.
3. 느린 클라이언트가 많아지면 active connection 증가와 지연 전파가 발생할 수 있다.

## Reconnect Policy
1. SSE 재연결은 새 요청으로 간주한다.
2. 서버는 중간 offset/token 상태를 복원하지 않는다.

## 운영 주의사항
1. 프록시/로드밸런서 idle timeout은 stream duration보다 크게 설정해야 한다.
2. 장시간 연결 증가 시 worker 수, keep-alive, timeout 정책을 함께 튜닝한다.
3. 오디오 chunk streaming/WebSocket/gRPC는 후속 태스크에서 분리 검토한다.
