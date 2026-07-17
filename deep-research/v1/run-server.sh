#!/bin/bash
set -e

cd "$(dirname "$0")"

export ENV_FILE="$(pwd)/.env"

# Start API server in background
cd src
uvicorn main:app --host 0.0.0.0 --port 7100
