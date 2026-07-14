#!/bin/bash
set -e

cd "$(dirname "$0")"

# LLM 서버(localhost:901) 접근을 위해 host network 사용 (포트 7100 그대로 노출됨)
docker run --rm \
    --name deep-research-backend \
    --env-file .env \
    --network host \
    deep-research-backend
