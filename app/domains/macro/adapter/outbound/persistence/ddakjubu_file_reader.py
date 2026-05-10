import logging
from pathlib import Path

from app.domains.macro.application.port.ddakjubu_file_reader_port import DdakjubuFileReaderPort

logger = logging.getLogger(__name__)


class LocalDdakjubuFileReader(DdakjubuFileReaderPort):
    """로컬 파일 시스템에서 ddakjubu.md를 읽어오는 어댑터.

    상대 경로가 주어지면 프로젝트 루트(main.py가 위치한 디렉토리)를 기준으로 해석한다.
    """

    PROJECT_ROOT = Path(__file__).resolve().parents[6]

    def __init__(self, file_path: str):
        path = Path(file_path)
        self._path = path if path.is_absolute() else (self.PROJECT_ROOT / path)

    def read_content(self) -> str:
        if not self._path.exists():
            logger.info("[macro_file] ddakjubu.md 파일 없음 path=%s", self._path)
            return ""
        try:
            return self._path.read_text(encoding="utf-8")
        except OSError as e:
            logger.warning("[macro_file] ddakjubu.md 읽기 실패: %s", e)
            return ""
