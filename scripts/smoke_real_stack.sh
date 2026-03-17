#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
VLLM_BASE="${VLLM_BASE:-http://localhost:8001}"
TTS_BASE="${TTS_BASE:-http://localhost:9880}"

echo "[1/6] provider health"
curl -fsS "${VLLM_BASE}/health" | sed -n '1,120p'
echo
curl -fsS "${TTS_BASE}/health" | sed -n '1,120p'
echo

echo "[2/6] api ready"
curl -fsS "${API_BASE}/ready" | sed -n '1,160p'
echo

echo "[3/6] sync chat text"
curl -fsS -X POST "${API_BASE}/api/v1/chat" \
  -H "content-type: application/json" \
  -d '{"session_id":"real-sync","message":"실서버 스모크 테스트","response_mode":"text"}' \
  | sed -n '1,220p'
echo

echo "[4/6] sync chat text_audio"
curl -fsS -X POST "${API_BASE}/api/v1/chat" \
  -H "content-type: application/json" \
  -d '{"session_id":"real-audio","message":"실서버 오디오 테스트","response_mode":"text_audio","voice_id":"ko_female_1"}' \
  | sed -n '1,220p'
echo

echo "[5/6] stream chat"
curl -fsS -N -X POST "${API_BASE}/api/v1/chat/stream" \
  -H "content-type: application/json" \
  -d '{"session_id":"real-stream","message":"실서버 스트리밍 테스트","response_mode":"text"}' \
  | sed -n '1,24p'
echo

echo "[6/6] metrics"
curl -fsS "${API_BASE}/metrics" | rg -n "chat_request_total|chat_stream_request_total|provider_latency_seconds|chat_stream_active_connections" | sed -n '1,40p'
