from typing import Optional

from pydantic import BaseModel

from app.common.exception.app_exception import AppException
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
from app.domains.ddakjubu2.application.response.learning_note_response import (
    LearningNoteDetailResponse,
    StockInsightDto,
)
from app.domains.ddakjubu2.application.usecase.get_learning_note_detail_usecase import (
    GetLearningNoteDetailUseCase,
    methodology_to_dto,
)
from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.domain.service.youtube_video_id_parser import (
    extract_video_id,
)


class LearnVideoResponse(BaseModel):
    already_learned: bool
    has_transcript: bool
    note: LearningNoteDetailResponse


class LearnSingleVideoUseCase:
    """YouTube URL/ID 하나를 지정해 즉시 학습한다 (자막→요약→인사이트→방법론→DB+md).

    이미 학습된 영상이면 LLM 호출 없이 기존 결과를 반환한다.
    """

    def __init__(
        self,
        video_fetch_port: Ddakjubu2VideoFetchPort,
        transcript_fetch_port: VideoTranscriptFetchPort,
        video_summarization_port: VideoSummarizationPort,
        video_learning_port: VideoLearningPort,
        methodology_extraction_port: MethodologyExtractionPort,
        note_writer_port: Ddakjubu2NoteWriterPort,
        note_repository_port: LearningNoteRepositoryPort,
        methodology_repository_port: MethodologyRepositoryPort,
        llm_model_label: str = "",
    ):
        self._video_fetch_port = video_fetch_port
        self._transcript_fetch_port = transcript_fetch_port
        self._video_summarization_port = video_summarization_port
        self._video_learning_port = video_learning_port
        self._methodology_extraction_port = methodology_extraction_port
        self._note_writer_port = note_writer_port
        self._note_repository_port = note_repository_port
        self._methodology_repository_port = methodology_repository_port
        self._llm_model_label = llm_model_label

    async def execute(self, video_input: str) -> LearnVideoResponse:
        video_id = extract_video_id(video_input)
        if video_id is None:
            raise AppException(
                status_code=400,
                message="유효한 YouTube URL 또는 11자 video_id 가 아닙니다.",
            )

        # 이미 학습된 영상이면 기존 결과 반환 (LLM 비용 없음)
        existing = await self._get_detail(video_id)
        if existing is not None:
            print(f"[ddakjubu2_single] 이미 학습된 영상 video_id={video_id}", flush=True)
            return LearnVideoResponse(
                already_learned=True,
                has_transcript=False,
                note=existing,
            )

        videos = await self._video_fetch_port.fetch_videos_by_ids([video_id])
        if not videos:
            raise AppException(
                status_code=404,
                message=(
                    "YouTube 에서 영상 정보를 가져오지 못했습니다. "
                    "video_id 또는 YOUTUBE_API_KEY 설정을 확인해 주세요."
                ),
            )
        video = videos[0]
        print(
            f"[ddakjubu2_single] 학습 시작 video_id={video_id} "
            f"title={video.title[:50]}",
            flush=True,
        )

        try:
            video.transcript = await self._transcript_fetch_port.fetch_transcript(
                video_id
            )
            print(
                f"[ddakjubu2_single] 자막 길이={len(video.transcript)}", flush=True
            )
        except Exception as e:
            print(
                f"[ddakjubu2_single] 자막 조회 실패(요약만으로 진행) error={e}",
                flush=True,
            )
            video.transcript = ""

        video.summary = await self._video_summarization_port.summarize(video)
        note: LearningNote = await self._video_learning_port.learn(video)

        # DB 저장
        await self._note_repository_port.save_note(
            note, has_transcript=bool(video.transcript), source="manual"
        )

        # 방법론 추출 (실패해도 노트는 유지)
        methodology_dto = None
        try:
            methodology = await self._methodology_extraction_port.extract(video, note)
            await self._methodology_repository_port.save(
                methodology, model=self._llm_model_label
            )
            methodology_dto = methodology_to_dto(methodology)
        except Exception as e:
            print(f"[ddakjubu2_single] 방법론 추출 실패 error={e}", flush=True)

        # 기존 md 파일에도 append (video_id 중복 시 skip)
        try:
            if video_id not in self._note_writer_port.load_existing_video_ids():
                self._note_writer_port.append_notes([note])
        except Exception as e:
            print(f"[ddakjubu2_single] md 저장 실패 error={e}", flush=True)

        return LearnVideoResponse(
            already_learned=False,
            has_transcript=bool(video.transcript),
            note=LearningNoteDetailResponse(
                video_id=note.video_id,
                video_title=note.video_title,
                channel_name=note.channel_name,
                program_category=note.program_category,
                published_at=note.published_at,
                learned_at=note.learned_at,
                summary=note.summary,
                stock_insights=[
                    StockInsightDto(
                        stock_name=i.stock_name,
                        ticker=i.ticker,
                        investment_view=i.investment_view,
                        key_claims=i.key_claims,
                        supporting_evidence=i.supporting_evidence,
                    )
                    for i in note.stock_insights
                ],
                methodology=methodology_dto,
            ),
        )

    async def _get_detail(
        self, video_id: str
    ) -> Optional[LearningNoteDetailResponse]:
        usecase = GetLearningNoteDetailUseCase(
            note_repository_port=self._note_repository_port,
            methodology_repository_port=self._methodology_repository_port,
        )
        return await usecase.execute(video_id)
