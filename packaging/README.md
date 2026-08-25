# 데스크톱 백엔드 빌드 (Windows 전용)

`pdf_to_ppt` 도메인만 담은 경량 sidecar 백엔드를 단일 `.exe` 로 빌드한다.
PyInstaller 는 크로스 컴파일을 지원하지 않으므로 **반드시 Windows 머신/CI에서**
실행해야 한다.

```powershell
pip install pyinstaller pypdf python-pptx fastapi "uvicorn[standard]" pydantic pydantic-settings openai
pyinstaller packaging/pyinstaller.spec
```

빌드 결과: `dist/pdf-to-ppt-backend.exe`

이 파일을 `FPPS_frontend/apps/desktop/resources/backend/pdf-to-ppt-backend.exe` 로
복사한 뒤 `apps/desktop` 에서 `npm run dist` 를 실행하면 최종 설치 프로그램(.exe)이
만들어진다.
