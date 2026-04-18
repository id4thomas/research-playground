#!/usr/bin/env bash
# Start the doclayout Triton server.
# Requires: venv-builder/env.tar.gz (run venv-builder/build_env.sh first)
#           .env with WEIGHTS_DIR pointing to local weights directory
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

IMAGE="nvcr.io/nvidia/tritonserver:26.03-py3"
CONTAINER_NAME="doclayout-triton"
ENV_TARBALL="$(pwd)/venv-builder/env.tar.gz"

if [ ! -f "${ENV_TARBALL}" ]; then
  echo "ERROR: ${ENV_TARBALL} not found. Run venv-builder/build_env.sh first." >&2
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "ERROR: .env not found. Copy .env.example to .env and set WEIGHTS_DIR." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

: "${WEIGHTS_DIR:?WEIGHTS_DIR must be set in .env}"
: "${TRITON_HTTP_PORT:=8000}"
: "${TRITON_GRPC_PORT:=8001}"
: "${TRITON_METRICS_PORT:=8002}"

if [ ! -d "${WEIGHTS_DIR}" ]; then
  echo "ERROR: WEIGHTS_DIR='${WEIGHTS_DIR}' does not exist." >&2
  exit 1
fi

docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

docker run --rm \
  --name "${CONTAINER_NAME}" \
  --gpus all \
  --shm-size=2g \
  -e DOCLAYOUT_MODEL_PATH=/weights \
  -e DOCLAYOUT_THRESHOLD="${DOCLAYOUT_THRESHOLD:-0.5}" \
  -v "${WEIGHTS_DIR}:/weights:ro" \
  -v "${ENV_TARBALL}:/opt/env.tar.gz:ro" \
  -v "$(pwd)/model:/models/PP-DocLayoutV3" \
  -p "${TRITON_HTTP_PORT}:8000" \
  -p "${TRITON_GRPC_PORT}:8001" \
  -p "${TRITON_METRICS_PORT}:8002" \
  "${IMAGE}" \
  tritonserver --model-repository=/models --log-verbose=1
