from datetime import date
from typing import Optional

from app.domains.ddakjubu2.application.port.learning_note_repository_port import (
    LearningNoteRepositoryPort,
)
from app.domains.ddakjubu2.application.response.learning_note_response import (
    LearningNoteListItem,
    LearningNoteListResponse,
)

SUMMARY_PREVIEW_LENGTH = 200


class GetLearningNotesUseCase:
    def __init__(self, note_repository_port: LearningNoteRepositoryPort):
        self._note_repository_port = note_repository_port

    async def execute(
        self,
        limit: int = 20,
        offset: int = 0,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> LearningNoteListResponse:
        items, total = await self._note_repository_port.find_notes(
            limit=limit, offset=offset, date_from=date_from, date_to=date_to
        )
        return LearningNoteListResponse(
            items=[
                LearningNoteListItem(
                    video_id=item.video_id,
                    video_title=item.video_title,
                    program_category=item.program_category,
                    published_at=item.published_at,
                    summary_preview=self._preview(item.summary),
                    stock_names=item.stock_names,
                    has_transcript=item.has_transcript,
                    has_methodology=item.has_methodology,
                )
                for item in items
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def _preview(summary: str) -> str:
        text = (summary or "").strip()
        if len(text) <= SUMMARY_PREVIEW_LENGTH:
            return text
        return text[:SUMMARY_PREVIEW_LENGTH] + "…"
