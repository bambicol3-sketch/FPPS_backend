import asyncio
from datetime import datetime, timezone
from typing import List, Optional

from app.domains.ddakjubu2.application.port.ddakjubu2_note_writer_port import (
    Ddakjubu2NoteWriterPort,
)
from app.domains.ddakjubu2.application.port.ddakjubu2_video_fetch_port import (
    Ddakjubu2VideoFetchPort,
)
from app.domains.ddakjubu2.application.port.learning_note_repository_port import (
    LearningNoteRepositoryPort,
)
from app.domains.ddakjubu2.application.port.methodology_extraction_port import (
    MethodologyExtractionPort,
)
from app.domains.ddakjubu2.application.port.methodology_repository_port import (
    MethodologyRepositoryPort,
)
from app.domains.ddakjubu2.application.port.video_learning_port import VideoLearningPort
from app.domains.ddakjubu2.application.port.video_summarization_port import (
    VideoSummarizationPort,
)
from app.domains.ddakjubu2.application.port.video_transcript_fetch_port import (
    VideoTranscriptFetchPort,
)
from app.domains.ddakjubu2.application.response.learn_ddakjubu2_response import (
    LearnDdakjubu2Response,
    LearnedVideoItem,
)
from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo

DDAKJUBU2_CHANNEL_IDS: List[str] = [
    "UC2-YdiOkgqWzIdDwCYW1utw",  # 딱딱한 주식 부드럽게 | 딱주부TV
]

# 수집 하한 일시: 2024-06-09 이후 업로드된 영상만 학습 대상
DDAKJUBU2_PUBLISHED_AFTER = datetime(2024, 6, 9, 0, 0, 0, tzinfo=timezone.utc)

# 배치 저장 크기: N개마다 파일 flush 하여 장시간 실행 중 OpenAI 장애/중단 시 진행분 보존
BATCH_SAVE_SIZE = 10


class LearnDdakjubu2VideosUseCase:
    """딱주부TV 채널의 모든 영상을 LLM 으로 학습하고 ddakjubu2.md 에 저장한다."""

    def __init__(
        self,
        video_fetch_port: Ddakjubu2VideoFetchPort,
        video_summarization_port: VideoSummarizationPort,
        video_learning_port: VideoLearningPort,
        note_writer_port: Ddakjubu2NoteWriterPort,
        transcript_fetch_port: Optional[VideoTranscriptFetchPort] = None,
        methodology_extraction_port: Optional[MethodologyExtractionPort] = None,
        note_repository_port: Optional[LearningNoteRepositoryPort] = None,
        methodology_repository_port: Optional[MethodologyRepositoryPort] = None,
        transcript_sleep_seconds: int = 120,
        llm_model_label: str = "",
    ):
        self._video_fetch_port = video_fetch_port
        self._video_summarization_port = video_summarization_port
        self._video_learning_port = video_learning_port
        self._note_writer_port = note_writer_port
        self._transcript_fetch_port = transcript_fetch_port
        self._methodology_extraction_port = methodology_extraction_port
        self._note_repository_port = note_repository_port
        self._methodology_repository_port = methodology_repository_port
        self._transcript_sleep_seconds = transcript_sleep_seconds
        self._llm_model_label = llm_model_label

    async def _fetch_transcript_safely(self, video: SourceVideo) -> None:
        """자막을 시도하되 실패해도 파이프라인을 중단하지 않는다."""
        if self._transcript_fetch_port is None:
            return
        try:
            video.transcript = await self._transcript_fetch_port.fetch_transcript(
                video.video_id
            )
            print(
                f"[ddakjubu2]   - 자막 길이={len(video.transcript)}",
                flush=True,
            )
        except Exception as e:
            print(
                f"[ddakjubu2]   ! 자막 조회 실패(요약만으로 진행) "
                f"video_id={video.video_id} error={e}",
                flush=True,
            )
            video.transcript = ""

    async def _persist_note_and_methodology(
        self, video: SourceVideo, note: LearningNote
    ) -> None:
        """DB 저장 + 방법론 추출. 실패해도 md 저장 파이프라인은 계속 진행한다."""
        if self._note_repository_port is not None:
            try:
                if not await self._note_repository_port.exists(note.video_id):
                    await self._note_repository_port.save_note(
                        note,
                        has_transcript=bool(video.transcript),
                        source="daily",
                    )
            except Exception as e:
                print(
                    f"[ddakjubu2]   ! 노트 DB 저장 실패 "
                    f"video_id={note.video_id} error={e}",
                    flush=True,
                )

        if (
            self._methodology_extraction_port is not None
            and self._methodology_repository_port is not None
        ):
            try:
                if not await self._methodology_repository_port.exists(note.video_id):
                    methodology = await self._methodology_extraction_port.extract(
                        video, note
                    )
                    await self._methodology_repository_port.save(
                        methodology, model=self._llm_model_label
                    )
                    print(
                        f"[ddakjubu2]   - 방법론 추출 "
                        f"steps={len(methodology.analysis_steps)}",
                        flush=True,
                    )
            except Exception as e:
                print(
                    f"[ddakjubu2]   ! 방법론 추출 실패 "
                    f"video_id={note.video_id} error={e}",
                    flush=True,
                )

    async def execute(self) -> LearnDdakjubu2Response:
        print("[ddakjubu2] 학습 파이프라인 시작")

        if not DDAKJUBU2_CHANNEL_IDS:
            print("[ddakjubu2] 채널 목록이 비어있어 영상 조회를 수행하지 않습니다.")
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=0,
                videos=[],
            )

        print(
            f"[ddakjubu2] 영상 조회 요청 생성: channels={DDAKJUBU2_CHANNEL_IDS}, "
            f"published_after={DDAKJUBU2_PUBLISHED_AFTER.isoformat()}"
        )
        source_videos = await self._video_fetch_port.fetch_channel_videos(
            channel_ids=DDAKJUBU2_CHANNEL_IDS,
            published_after=DDAKJUBU2_PUBLISHED_AFTER,
        )
        print(f"[ddakjubu2] 채널에서 조회된 영상 수: {len(source_videos)}")

        if not source_videos:
            print("[ddakjubu2] 학습 대상 영상이 존재하지 않습니다.")
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=0,
                videos=[],
            )

        sorted_videos = self._sort_and_deduplicate(source_videos)
        print(f"[ddakjubu2] 중복 제거 및 정렬 후 영상 수: {len(sorted_videos)}")

        existing_video_ids = self._note_writer_port.load_existing_video_ids()
        print(f"[ddakjubu2] 기존 파일에 기록된 video_id 수: {len(existing_video_ids)}")

        new_videos = [v for v in sorted_videos if v.video_id not in existing_video_ids]
        skipped = len(sorted_videos) - len(new_videos)
        print(f"[ddakjubu2] 신규 학습 대상: {len(new_videos)}, 중복 skip: {skipped}")

        if not new_videos:
            print("[ddakjubu2] 새로 학습할 영상이 없습니다.")
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=skipped,
                videos=[],
            )

        batch_buffer: List[LearningNote] = []
        all_notes: List[LearningNote] = []
        file_path = ""
        for idx, video in enumerate(new_videos, start=1):
            print(
                f"[ddakjubu2] ({idx}/{len(new_videos)}) 학습 시작 "
                f"video_id={video.video_id} title={video.title[:40]}",
                flush=True,
            )
            try:
                await self._fetch_transcript_safely(video)
                video.summary = await self._video_summarization_port.summarize(video)
                note = await self._video_learning_port.learn(video)
                print(
                    f"[ddakjubu2]   - 요약 {len(video.summary)}자, "
                    f"종목 {len(note.stock_insights)}개",
                    flush=True,
                )
                await self._persist_note_and_methodology(video, note)
                batch_buffer.append(note)
                all_notes.append(note)
            except Exception as e:
                print(
                    f"[ddakjubu2]   ! 학습 실패 video_id={video.video_id} error={e}",
                    flush=True,
                )
                continue
            finally:
                # 자막 스크래핑 사용 시 IP 차단 방지를 위해 영상 간 대기
                if (
                    self._transcript_fetch_port is not None
                    and idx < len(new_videos)
                    and self._transcript_sleep_seconds > 0
                ):
                    print(
                        f"[ddakjubu2] 다음 영상 전 대기 "
                        f"{self._transcript_sleep_seconds}초",
                        flush=True,
                    )
                    await asyncio.sleep(self._transcript_sleep_seconds)

            if len(batch_buffer) >= BATCH_SAVE_SIZE:
                file_path = self._note_writer_port.append_notes(batch_buffer)
                print(
                    f"[ddakjubu2] 배치 저장 완료 batch={len(batch_buffer)} "
                    f"cumulative={len(all_notes)}/{len(new_videos)} path={file_path}",
                    flush=True,
                )
                batch_buffer = []

        if batch_buffer:
            file_path = self._note_writer_port.append_notes(batch_buffer)
            print(
                f"[ddakjubu2] 마지막 배치 저장 완료 batch={len(batch_buffer)} "
                f"cumulative={len(all_notes)}/{len(new_videos)} path={file_path}",
                flush=True,
            )

        if not all_notes:
            print("[ddakjubu2] 학습 결과가 존재하지 않습니다.")
            return LearnDdakjubu2Response(
                file_path="",
                processed_count=0,
                skipped_duplicate_count=skipped,
                videos=[],
            )

        print(
            f"[ddakjubu2] 파이프라인 종료: file_path={file_path}, "
            f"processed={len(all_notes)}, skipped_duplicates={skipped}",
            flush=True,
        )

        items = [
            LearnedVideoItem(
                video_id=note.video_id,
                video_title=note.video_title,
                program_category=note.program_category,
                stock_count=len(note.stock_insights),
            )
            for note in all_notes
        ]

        return LearnDdakjubu2Response(
            file_path=file_path,
            processed_count=len(all_notes),
            skipped_duplicate_count=skipped,
            videos=items,
        )

    @staticmethod
    def _sort_and_deduplicate(videos: List[SourceVideo]) -> List[SourceVideo]:
        unique: dict[str, SourceVideo] = {}
        for video in videos:
            if video.video_id and video.video_id not in unique:
                unique[video.video_id] = video
        return sorted(
            unique.values(),
            key=lambda v: v.published_at,
            reverse=True,
        )
