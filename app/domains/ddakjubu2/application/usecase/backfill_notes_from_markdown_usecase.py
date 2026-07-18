from typing import List, Tuple

from app.domains.ddakjubu2.application.port.ddakjubu2_note_reader_port import (
    Ddakjubu2NoteReaderPort,
)
from app.domains.ddakjubu2.application.port.learning_note_repository_port import (
    LearningNoteRepositoryPort,
)
from app.domains.ddakjubu2.application.response.learning_note_response import (
    BackfillResponse,
)


class BackfillNotesFromMarkdownUseCase:
    """기존 Markdown 학습 노트(ddakjubu2.md 등)를 DB 로 1회 이관한다. 멱등 실행 가능."""

    def __init__(
        self,
        note_repository_port: LearningNoteRepositoryPort,
        sources: List[Tuple[Ddakjubu2NoteReaderPort, bool]],
    ):
        """sources: (리더, has_transcript 플래그) 목록.

        ddakjubu2.md 는 자막 없이 학습됐으므로 False,
        ddakjubu2_enhanced.md 는 자막 포함이므로 True 를 전달한다.
        """
        self._note_repository_port = note_repository_port
        self._sources = sources

    async def execute(self) -> BackfillResponse:
        parsed = 0
        inserted = 0
        skipped = 0
        failed = 0
        source_files: List[str] = []

        for reader, has_transcript in self._sources:
            source_files.append(reader.source_path())
            notes = reader.read_notes()
            parsed += len(notes)
            for note in notes:
                try:
                    if await self._note_repository_port.exists(note.video_id):
                        skipped += 1
                        continue
                    await self._note_repository_port.save_note(
                        note, has_transcript=has_transcript, source="backfill"
                    )
                    inserted += 1
                except Exception as e:
                    failed += 1
                    print(
                        f"[ddakjubu2_backfill] 저장 실패 video_id={note.video_id} "
                        f"error={e}",
                        flush=True,
                    )

        print(
            f"[ddakjubu2_backfill] 완료 parsed={parsed} inserted={inserted} "
            f"skipped={skipped} failed={failed}",
            flush=True,
        )
        return BackfillResponse(
            parsed_count=parsed,
            inserted_count=inserted,
            skipped_existing_count=skipped,
            failed_count=failed,
            source_files=source_files,
        )
