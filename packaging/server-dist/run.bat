@echo off
REM 셀프호스팅 실행 스크립트 (Windows).
REM PostgreSQL(+ pgvector 확장)/Redis 는 직접 준비해 .env 에 연결정보를 채워야 한다.
cd /d "%~dp0"

if not exist ".env" (
  echo .env 파일이 없습니다. .env.example 을 복사해 값을 채운 뒤 다시 실행하세요.
  exit /b 1
)

if not exist ".venv" (
  python -m venv .venv
)
call .venv\Scripts\activate.bat

pip install --upgrade pip
pip install -r requirements.txt

alembic upgrade head

if "%PORT%"=="" set PORT=33333
uvicorn main:app --host 0.0.0.0 --port %PORT%
