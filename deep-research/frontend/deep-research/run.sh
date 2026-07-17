#!/bin/bash
set -e

cd "$(dirname "$0")"

# 정적 페이지 서빙 (API 주소는 ?api=http://... 쿼리로 변경 가능, 기본 http://localhost:7100)
python -m http.server "${PORT:-7861}"
