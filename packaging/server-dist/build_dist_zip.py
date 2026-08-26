"""셀프호스팅용 배포 zip 패키지를 만든다.

포함: app/, alembic/, alembic.ini, main.py, requirements.txt, .env.example,
      run.sh, run.bat, README.md(배포판용)
제외: docs/, generated_pptx/, parse_cache/, .git, __pycache__ 등 개발용 산출물
      (원본 저장소의 서브셋만 담는다 — Docker/DB 자체는 포함하지 않음)

실행: python packaging/server-dist/build_dist_zip.py
결과: dist/antelligen-backend-<git short sha 또는 타임스탬프>.zip
"""

import os
import subprocess
import zipfile
from datetime import datetime

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
DIST_DIR = os.path.join(REPO_ROOT, "dist")
PACKAGING_DIR = os.path.dirname(os.path.abspath(__file__))

INCLUDE_PATHS = [
    "app",
    "alembic",
    "alembic.ini",
    "main.py",
    "requirements.txt",
    ".env.example",
]

EXCLUDE_DIR_NAMES = {"__pycache__", ".pytest_cache"}


def _version_tag() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return datetime.now().strftime("%Y%m%d_%H%M%S")


def _add_tree(zf: zipfile.ZipFile, src_root: str, arc_root: str) -> None:
    for dirpath, dirnames, filenames in os.walk(src_root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_NAMES]
        for name in filenames:
            if name.endswith((".pyc", ".pyo")):
                continue
            full_path = os.path.join(dirpath, name)
            rel_path = os.path.relpath(full_path, src_root)
            zf.write(full_path, os.path.join(arc_root, rel_path))


def main() -> None:
    os.makedirs(DIST_DIR, exist_ok=True)
    zip_path = os.path.join(DIST_DIR, f"antelligen-backend-{_version_tag()}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path in INCLUDE_PATHS:
            src = os.path.join(REPO_ROOT, rel_path)
            if not os.path.exists(src):
                print(f"[경고] 건너뜀 (존재하지 않음): {rel_path}")
                continue
            if os.path.isdir(src):
                _add_tree(zf, src, os.path.join("antelligen-backend", rel_path))
            else:
                zf.write(src, os.path.join("antelligen-backend", rel_path))

        for script_name in ("run.sh", "run.bat", "README.md"):
            zf.write(
                os.path.join(PACKAGING_DIR, script_name),
                os.path.join("antelligen-backend", script_name),
            )

    print(f"생성 완료: {zip_path}")


if __name__ == "__main__":
    main()
