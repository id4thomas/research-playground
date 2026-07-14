#!/bin/bash
set -e

cd "$(dirname "$0")"

docker build -t deep-research-backend .
