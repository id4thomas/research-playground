#!/bin/bash
set -e

cd "$(dirname "$0")"

API_URL=${API_URL:-http://localhost:7100/search} python app.py
