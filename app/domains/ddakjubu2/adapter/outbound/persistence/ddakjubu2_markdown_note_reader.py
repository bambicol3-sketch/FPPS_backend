from pathlib import Path
from typing import List

from app.domains.ddakjubu2.application.port.ddakjubu2_note_reader_port import (
    Ddakjubu2NoteReaderPort,
)
from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.domain.service.learning_note_markdown_parser import (
    LearningNoteMarkdownParser,
)

# app/domains/ddakjubu2/adapter/outbound/persistence/ → 프로젝트 루트
_PROJECT_ROOT = Path(__file__).resolve().parents[6]


class Ddakjubu2MarkdownNoteReader(Ddakjubu2NoteReaderPort):
    """기존 ddakjubu2*.md 파일을 읽어 LearningNote 목록으로 파싱하는 백필용 어댑터."""

    def __init__(self, file_path: str):
        path = Path(file_path)
        if not path.is_absolute():
            path = _PROJECT_ROOT / path
        self._path = path
        self._parser = LearningNoteMarkdownParser()

    def read_notes(self) -> List[LearningNote]:
        if not self._path.exists():
            print(f"[ddakjubu2_backfill] 파일 없음 path={self._path}")
            return []
        try:
            content = self._path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"[ddakjubu2_backfill] 파일 읽기 실패 path={self._path} error={e}")
            return []
        notes = self._parser.parse(content)
        print(
            f"[ddakjubu2_backfill] 파싱 완료 path={self._path} notes={len(notes)}"
        )
        return notes

    def source_path(self) -> str:
        return str(self._path)
