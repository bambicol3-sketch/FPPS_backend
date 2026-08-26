# PDF-to-PPT 데스크톱 sidecar 백엔드를 단일 실행파일로 빌드하는 PyInstaller spec.
#
# 반드시 타깃 OS(Windows)에서 실행해야 한다 — PyInstaller는 크로스 컴파일을
# 지원하지 않으므로 Windows용 .exe는 Windows 머신/CI에서만 만들 수 있다.
#
# 빌드 방법 (Windows, 레포 루트에서):
#   pip install pyinstaller pypdf python-pptx fastapi uvicorn[standard] \
#       pydantic pydantic-settings openai
#   pyinstaller packaging/pyinstaller.spec
#   → dist/pdf-to-ppt-backend.exe 생성됨
#   → 이 파일을 FPPS_frontend/apps/desktop/resources/backend/ 로 복사

import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(SPEC)), ".."))

a = Analysis(
    [os.path.join(repo_root, "packaging", "desktop_app.py")],
    pathex=[repo_root],
    binaries=[],
    datas=[],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="pdf-to-ppt-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
)
