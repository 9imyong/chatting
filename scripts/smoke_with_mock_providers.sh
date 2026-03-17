#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

API_PORT="${API_PORT:-18000}"
VLLM_PORT="${VLLM_PORT:-18001}"
TTS_PORT="${TTS_PORT:-19880}"

cleanup() {
  for pid in "${API_PID:-}" "${VLLM_PID:-}" "${TTS_PID:-}"; do
    if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" >/dev/null 2>&1 || true
      wait "$pid" >/dev/null 2>&1 || true
    fi
  done
}
trap cleanup EXIT

echo "[1/6] start mock providers"
python3 -m uvicorn app.mock_servers.vllm_mock:app --host 127.0.0.1 --port "$VLLM_PORT" >/tmp/vllm-mock.log 2>&1 &
VLLM_PID=$!
python3 -m uvicorn app.mock_servers.gptsovits_mock:app --host 127.0.0.1 --port "$TTS_PORT" >/tmp/gptsovits-mock.log 2>&1 &
TTS_PID=$!

sleep 1
curl -fsS "http://127.0.0.1:${VLLM_PORT}/health" >/dev/null
curl -fsS "http://127.0.0.1:${TTS_PORT}/health" >/dev/null

echo "[2/6] start api with real-adapter mode"
APP_NAME=chat-model-serving-smoke \
LLM_PROVIDER=vllm \
TTS_PROVIDER=gptsovits \
SESSION_BACKEND=memory \
VLLM_BASE_URL="http://127.0.0.1:${VLLM_PORT}" \
GPT_SOVITS_BASE_URL="http://127.0.0.1:${TTS_PORT}" \
HTTP_RETRY_COUNT=0 \
python3 -m uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" >/tmp/chat-api-smoke.log 2>&1 &
API_PID=$!

sleep 1
echo "[3/6] ready check"
curl -fsS "http://127.0.0.1:${API_PORT}/ready" | sed -n '1,120p'

echo "[4/6] sync chat smoke"
curl -fsS -X POST "http://127.0.0.1:${API_PORT}/api/v1/chat" \
  -H "content-type: application/json" \
  -d '{"session_id":"smoke-sync","message":"hello smoke","response_mode":"text_audio","voice_id":"ko_female_1"}' \
  | sed -n '1,200p'

echo "[5/6] stream chat smoke"
curl -fsS -N -X POST "http://127.0.0.1:${API_PORT}/api/v1/chat/stream" \
  -H "content-type: application/json" \
  -d '{"session_id":"smoke-stream","message":"stream smoke test","response_mode":"text"}' \
  | sed -n '1,20p'

echo "[6/6] metrics probe"
curl -fsS "http://127.0.0.1:${API_PORT}/metrics" | rg -n "chat_request_total|chat_stream_request_total|provider_latency_seconds" | sed -n '1,20p'

echo "smoke completed"
