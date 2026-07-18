import logging
import time as _time

from app.domains.ddakjubu2.adapter.outbound.external.openai_video_learning_client import (
    OpenAIVideoLearningClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_video_summarization_client import (
    OpenAIVideoSummarizationClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.youtube_ddakjubu2_video_client import (
    YoutubeDdakjubu2VideoClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_methodology_extraction_client import (
    OpenAIMethodologyExtractionClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_methodology_merge_client import (
    OpenAIMethodologyMergeClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.youtube_transcript_api_client import (
    YoutubeTranscriptApiClient,
    build_proxy_config_from_settings,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.ddakjubu2_markdown_file_writer import (
    Ddakjubu2MarkdownFileWriter,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.learning_note_repository_impl import (
    LearningNoteRepositoryImpl,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.methodology_repository_impl import (
    MethodologyRepositoryImpl,
)
from app.domains.ddakjubu2.application.usecase.learn_ddakjubu2_videos_usecase import (
    LearnDdakjubu2VideosUseCase,
)
from app.domains.ddakjubu2.application.usecase.rebuild_master_methodology_usecase import (
    RebuildMasterMethodologyUseCase,
)
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


async def job_learn_ddakjubu2_videos():
    """Daily 05:00 KST: 딱주부TV 채널의 최근 추가된 영상을 학습해 ddakjubu2.md 에 업데이트."""
    start = _time.monotonic()
    print("[Scheduler][Ddakjubu2] 매일 05:00 KST 학습 job 시작", flush=True)
    logger.info("[Scheduler][Ddakjubu2] Starting daily learning job")

    try:
        settings = get_settings()

        video_fetch_port = YoutubeDdakjubu2VideoClient(api_key=settings.youtube_api_key)
        video_summarization_port = OpenAIVideoSummarizationClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
        )
        video_learning_port = OpenAIVideoLearningClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
        )
        note_writer_port = Ddakjubu2MarkdownFileWriter(
            file_path=settings.ddakjubu2_md_path
        )
        transcript_fetch_port = YoutubeTranscriptApiClient(
            proxy_config=build_proxy_config_from_settings(settings)
        )
        methodology_extraction_port = OpenAIMethodologyExtractionClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
        )

        usecase = LearnDdakjubu2VideosUseCase(
            video_fetch_port=video_fetch_port,
            video_summarization_port=video_summarization_port,
            video_learning_port=video_learning_port,
            note_writer_port=note_writer_port,
            transcript_fetch_port=transcript_fetch_port,
            methodology_extraction_port=methodology_extraction_port,
            note_repository_port=LearningNoteRepositoryImpl(),
            methodology_repository_port=MethodologyRepositoryImpl(),
            transcript_sleep_seconds=settings.ddakjubu2_daily_transcript_sleep_seconds,
            llm_model_label=settings.ddakjubu2_llm_model,
        )

        result = await usecase.execute()

        elapsed = _time.monotonic() - start
        print(
            f"[Scheduler][Ddakjubu2] 완료 file_path={result.file_path} "
            f"processed={result.processed_count} "
            f"skipped_duplicates={result.skipped_duplicate_count} "
            f"elapsed={elapsed:.1f}s",
            flush=True,
        )
        logger.info(
            "[Scheduler][Ddakjubu2] Complete — file_path=%s, processed=%d, "
            "skipped_duplicates=%d (%.1fs)",
            result.file_path,
            result.processed_count,
            result.skipped_duplicate_count,
            elapsed,
        )
    except Exception as e:
        elapsed = _time.monotonic() - start
        print(
            f"[Scheduler][Ddakjubu2] 실패 elapsed={elapsed:.1f}s error={e}",
            flush=True,
        )
        logger.error(
            "[Scheduler][Ddakjubu2] Failed after %.1fs: %s", elapsed, str(e)
        )


async def job_rebuild_master_methodology():
    """Weekly Sun 06:00 KST: 최근 영상 방법론들을 통합해 마스터 방법론 새 버전 생성."""
    start = _time.monotonic()
    print("[Scheduler][Ddakjubu2] 주간 마스터 방법론 재생성 job 시작", flush=True)
    logger.info("[Scheduler][Ddakjubu2] Starting weekly master methodology rebuild")

    try:
        settings = get_settings()

        usecase = RebuildMasterMethodologyUseCase(
            methodology_repository_port=MethodologyRepositoryImpl(),
            methodology_merge_port=OpenAIMethodologyMergeClient(
                api_key=settings.openai_api_key,
                model=settings.ddakjubu2_llm_model,
            ),
            max_videos=settings.ddakjubu2_master_merge_max_videos,
        )
        result = await usecase.execute()

        elapsed = _time.monotonic() - start
        version = result.version if result else None
        print(
            f"[Scheduler][Ddakjubu2] 마스터 재생성 완료 version={version} "
            f"elapsed={elapsed:.1f}s",
            flush=True,
        )
        logger.info(
            "[Scheduler][Ddakjubu2] Master rebuild complete — version=%s (%.1fs)",
            version,
            elapsed,
        )
    except Exception as e:
        elapsed = _time.monotonic() - start
        print(
            f"[Scheduler][Ddakjubu2] 마스터 재생성 실패 elapsed={elapsed:.1f}s error={e}",
            flush=True,
        )
        logger.error(
            "[Scheduler][Ddakjubu2] Master rebuild failed after %.1fs: %s",
            elapsed,
            str(e),
        )
