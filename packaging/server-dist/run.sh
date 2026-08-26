#!/usr/bin/env bash
# 셀프호스팅 실행 스크립트 (Linux/Mac).
# PostgreSQL(+ pgvector 확장)/Redis 는 직접 준비해 .env 에 연결정보를 채워야 한다.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
  echo ".env 파일이 없습니다. .env.example 을 복사해 값을 채운 뒤 다시 실행하세요."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

alembic upgrade head

uvicorn main:app --host 0.0.0.0 --port "${PORT:-33333}"
