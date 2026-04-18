#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

NAME="doclayout-venv-builder"
REQUIREMENTS_FILE="$(pwd)/requirements.txt"
OUTPUT_FILE="$(pwd)/env.tar.gz"

if [ ! -f "${REQUIREMENTS_FILE}" ]; then
  echo "ERROR: ${REQUIREMENTS_FILE} not found." >&2
  exit 1
fi

echo "==> Building ${NAME} ..."
docker build -t "${NAME}" .

echo "==> Packing env from requirements.txt ..."
docker rm -f "${NAME}" >/dev/null 2>&1 || true
docker run --name "${NAME}" \
  -v "${REQUIREMENTS_FILE}:/tmp/requirements.txt:ro" \
  "${NAME}"

echo "==> Copying to ${OUTPUT_FILE} ..."
docker cp "${NAME}:/tmp/venv.tar.gz" "${OUTPUT_FILE}"
docker rm "${NAME}" >/dev/null

echo ""
echo "Done: ${OUTPUT_FILE}"
