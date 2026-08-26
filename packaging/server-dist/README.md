# Antelligen Backend — 셀프호스팅 배포판

이 zip은 애플리케이션 코드만 포함합니다. PostgreSQL(+ pgvector 확장), Redis는
직접 준비해야 합니다. (원본 저장소의 `docker-compose.yml` 을 참고해 인프라를
구성할 수도 있지만, 이 zip 자체에는 포함되어 있지 않습니다.)

## 처음 설정

1. `.env.example` 을 `.env` 로 복사하고 값을 채운다 (DB/Redis 접속정보, OpenAI API 키 등)
2. Python 3.11+ 준비
3. Linux/Mac: `./run.sh`   /   Windows: `run.bat`

최초 실행 시 자동으로 다음을 수행합니다.

- 가상환경(`.venv`) 생성
- `requirements.txt` 설치
- `alembic upgrade head` (DB 마이그레이션)
- uvicorn 서버 기동 (기본 포트 33333, `PORT` 환경변수로 변경 가능)

## 참고

- PostgreSQL에 pgvector 확장 자체는 미리 설치되어 있어야 합니다 (서버 기동 시
  `CREATE EXTENSION IF NOT EXISTS vector` 를 자동 실행하긴 하지만, 확장
  바이너리가 DB 서버에 설치돼 있지 않으면 실패합니다).
- 이 배포판은 원본 git 저장소의 서브셋입니다 (문서/개발용 스크래치 파일 제외).
