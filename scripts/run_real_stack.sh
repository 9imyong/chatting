#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${ENV_FILE:-env/.env.real.example}"

echo "[1/3] validating compose"
docker compose -f docker-compose.real.yml --env-file "$ENV_FILE" config >/tmp/chat.real.compose.out

echo "[2/3] starting real stack"
docker compose -f docker-compose.real.yml --env-file "$ENV_FILE" up -d

echo "[3/3] endpoints"
echo "API       : http://localhost:8000"
echo "vLLM      : http://localhost:8001"
echo "GPT-SoVITS: http://localhost:9880"
echo
echo "next: bash scripts/smoke_real_stack.sh"
