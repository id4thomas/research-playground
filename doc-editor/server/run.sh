#!/usr/bin/env bash
# Production / container launcher. Uses the `uvicorn` on PATH (no venv, no reload).
# For local dev with the ./env virtualenv and hot reload, use run-local.sh instead.
set -euo pipefail

cd "$(dirname "$0")"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"

exec uvicorn --app-dir src main:app --host "$HOST" --port "$PORT"
