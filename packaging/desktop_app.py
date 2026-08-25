"""데스크톱(Electron) sidecar 전용 진입점.

main.py 의 전체 앱은 PostgreSQL/Redis/Kakao·Google OAuth 등 다수의 외부
인프라를 요구하지만, 데스크톱 배포판은 PDF-to-PPT 기능만 제공하므로 그런
인프라가 전혀 필요 없다. 그럼에도 공용 Settings 클래스(app.infrastructure.
config.settings)는 그 필드들을 필수(default 없음)로 요구하기 때문에,
여기서는 실행에 실제로 쓰이지 않는 필드들을 더미 값으로 채워 넣어 공용
Settings 클래스를 그대로 재사용한다. 실제 동작에 쓰이는 값은
OPENAI_API_KEY 하나뿐이다.

빌드: pyinstaller packaging/pyinstaller.spec (레포 루트에서 실행)
실행: python packaging/desktop_app.py [port]
"""

import os

_UNUSED_REQUIRED_SETTINGS_DEFAULTS = {
    "POSTGRES_USER": "unused",
    "POSTGRES_PASSWORD": "unused",
    "POSTGRES_HOST": "unused",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "unused",
    "NAVER_CLIENT_ID": "unused",
    "NAVER_CLIENT_SECRET": "unused",
    "ANTHROPIC_API_KEY": "unused",
    "JWT_SECRET_KEY": "unused",
    "KAKAO_CLIENT_ID": "unused",
    "KAKAO_REDIRECT_URI": "unused",
}
for _key, _value in _UNUSED_REQUIRED_SETTINGS_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

import sys  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.common.exception.global_exception_handler import (  # noqa: E402
    register_exception_handlers,
)
from app.domains.pdf_to_ppt.adapter.inbound.api.pdf_to_ppt_router import (  # noqa: E402
    router as pdf_to_ppt_router,
)

app = FastAPI(title="PDF to PPT Desktop Backend")

# 로컬 sidecar — Electron 렌더러(같은 기기의 127.0.0.1)에서만 접근하므로
# 퍼블릭 배포용 CORS 제약이 필요 없다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(pdf_to_ppt_router, prefix="/api/v1")
register_exception_handlers(app)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY 환경변수가 설정되어 있지 않습니다.", file=sys.stderr)
        sys.exit(1)

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    uvicorn.run(app, host="127.0.0.1", port=port)
