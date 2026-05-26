#!/bin/bash

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"

source env/bin/activate

uvicorn --app-dir src main:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload \
  --reload-dir src
