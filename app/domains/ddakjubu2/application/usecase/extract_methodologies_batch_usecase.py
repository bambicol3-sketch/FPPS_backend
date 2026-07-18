import asyncio
from datetime import datetime, timezone

from app.domains.ddakjubu2.application.port.learning_note_repository_port import (
    LearningNoteRepositoryPort,
)
from app.domains.ddakjubu2.application.port.methodology_extraction_port import (
    MethodologyExtractionPort,
)
from app.domains.ddakjubu2.application.port.methodology_repository_port import (
    MethodologyRepositoryPort,
)
from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo


class ExtractMethodologiesBatchUseCase:
    """방법론이 아직 없는 DB 노트들에 대해 방법론 추출 패스를 배치 실행한다.

    자막 없이 요약·인사이트만으로 추출하는 저해상도 배치 (백필 노트 대상).
    OpenAI 레이트리밋을 고려해 순차 실행 + sleep.
    """

    def __init__(
        self,
        note_repository_port: LearningNoteRepositoryPort,
        methodology_extraction_port: MethodologyExtractionPort,
        methodology_repository_port: MethodologyRepositoryPort,
        max_notes: int = 100,
        sleep_between_seconds: float = 1.0,
    ):
        self._note_repository_port = note_repository_port
        self._methodology_extraction_port = methodology_extraction_port
        self._methodology_repository_port = methodology_repository_port
        self._max_notes = max_notes
        self._sleep_between_seconds = sleep_between_seconds

    async def execute(self, model_label: str = "") -> dict:
        video_ids = await self._note_repository_port.find_video_ids_without_methodology(
            limit=self._max_notes
        )
        print(
            f"[ddakjubu2_methodology_batch] 추출 대상 {len(video_ids)}개",
            flush=True,
        )
        extracted = 0
        empty = 0
        failed = 0

        for idx, video_id in enumerate(video_ids, start=1):
            note = await self._note_repository_port.find_by_video_id(video_id)
            if note is None:
                continue
            source_video = SourceVideo(
                video_id=note.video_id,
                title=note.video_title,
                description="",
                transcript="",
                channel_id="",
                channel_name=note.channel_name,
                published_at=note.published_at,
                collected_at=datetime.now(timezone.utc),
                program_category=note.program_category,
                summary=note.summary,
            )
            try:
                methodology = await self._methodology_extraction_port.extract(
                    source_video, note
                )
                if methodology.is_empty():
                    empty += 1
                await self._methodology_repository_port.save(
                    methodology, model=model_label
                )
                extracted += 1
                print(
                    f"[ddakjubu2_methodology_batch] ({idx}/{len(video_ids)}) "
                    f"video_id={video_id} steps={len(methodology.analysis_steps)}",
                    flush=True,
                )
            except Exception as e:
                failed += 1
                print(
                    f"[ddakjubu2_methodology_batch] ! 추출 실패 "
                    f"video_id={video_id} error={e}",
                    flush=True,
                )

            if idx < len(video_ids) and self._sleep_between_seconds > 0:
                await asyncio.sleep(self._sleep_between_seconds)

        result = {
            "targeted": len(video_ids),
            "extracted": extracted,
            "empty_methodology": empty,
            "failed": failed,
        }
        print(f"[ddakjubu2_methodology_batch] 완료 {result}", flush=True)
        return result
