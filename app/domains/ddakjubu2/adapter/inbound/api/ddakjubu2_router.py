import asyncio
from datetime import date, datetime
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.ddakjubu2.adapter.outbound.cache.redis_applied_analysis_cache import (
    RedisAppliedAnalysisCache,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_methodology_apply_client import (
    OpenAIMethodologyApplyClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_methodology_extraction_client import (
    OpenAIMethodologyExtractionClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_methodology_merge_client import (
    OpenAIMethodologyMergeClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_video_learning_client import (
    OpenAIVideoLearningClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.openai_video_summarization_client import (
    OpenAIVideoSummarizationClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.stock_context_provider import (
    StockContextProvider,
)
from app.domains.ddakjubu2.adapter.outbound.external.youtube_ddakjubu2_video_client import (
    YoutubeDdakjubu2VideoClient,
)
from app.domains.ddakjubu2.adapter.outbound.external.youtube_transcript_api_client import (
    YoutubeTranscriptApiClient,
    build_proxy_config_from_settings,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.applied_analysis_repository_impl import (
    AppliedAnalysisRepositoryImpl,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.ddakjubu2_markdown_file_writer import (
    Ddakjubu2MarkdownFileWriter,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.ddakjubu2_markdown_note_reader import (
    Ddakjubu2MarkdownNoteReader,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.learning_note_repository_impl import (
    LearningNoteRepositoryImpl,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.methodology_repository_impl import (
    MethodologyRepositoryImpl,
)
from app.domains.ddakjubu2.application.request.apply_analysis_request import (
    ApplyAnalysisRequest,
)
from app.domains.ddakjubu2.application.usecase.apply_methodology_usecase import (
    ApplyMethodologyUseCase,
    GetAppliedAnalysisHistoryUseCase,
)
from app.domains.ddakjubu2.application.usecase.backfill_notes_from_markdown_usecase import (
    BackfillNotesFromMarkdownUseCase,
)
from app.domains.ddakjubu2.application.usecase.enhance_ddakjubu2_videos_usecase import (
    EnhanceDdakjubu2VideosUseCase,
)
from app.domains.ddakjubu2.application.usecase.extract_methodologies_batch_usecase import (
    ExtractMethodologiesBatchUseCase,
)
from app.domains.ddakjubu2.application.usecase.get_learning_note_detail_usecase import (
    GetLearningNoteDetailUseCase,
    methodology_to_dto,
)
from app.domains.ddakjubu2.application.usecase.get_learning_notes_usecase import (
    GetLearningNotesUseCase,
)
from app.domains.ddakjubu2.application.usecase.learn_ddakjubu2_videos_usecase import (
    LearnDdakjubu2VideosUseCase,
)
from app.domains.ddakjubu2.application.usecase.rebuild_master_methodology_usecase import (
    RebuildMasterMethodologyUseCase,
)
from app.domains.ddakjubu2.application.response.learning_note_response import (
    MasterMethodologyResponse,
)
from app.domains.stock.adapter.outbound.persistence.stock_repository_impl import (
    StockRepositoryImpl,
)
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/ddakjubu2", tags=["ddakjubu2"])


@router.post("/learn")
async def learn_ddakjubu2_videos():
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
    note_writer_port = Ddakjubu2MarkdownFileWriter(file_path=settings.ddakjubu2_md_path)

    usecase = LearnDdakjubu2VideosUseCase(
        video_fetch_port=video_fetch_port,
        video_summarization_port=video_summarization_port,
        video_learning_port=video_learning_port,
        note_writer_port=note_writer_port,
        transcript_fetch_port=YoutubeTranscriptApiClient(
            proxy_config=build_proxy_config_from_settings(settings)
        ),
        methodology_extraction_port=OpenAIMethodologyExtractionClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
        ),
        note_repository_port=LearningNoteRepositoryImpl(),
        methodology_repository_port=MethodologyRepositoryImpl(),
        transcript_sleep_seconds=settings.ddakjubu2_daily_transcript_sleep_seconds,
        llm_model_label=settings.ddakjubu2_llm_model,
    )
    response = await usecase.execute()

    return BaseResponse.ok(data=response, message="딱주부2 학습 노트 저장 완료")


@router.post("/enhance")
async def enhance_ddakjubu2_videos(background_tasks: BackgroundTasks):
    """2026년 업로드 영상을 자막 포함으로 재학습하여 별도 파일에 저장한다.

    10분/영상 페이스로 진행되어 수 시간이 걸리므로 HTTP 응답은 즉시 반환하고
    실제 파이프라인은 백그라운드로 실행된다.
    """
    settings = get_settings()

    video_fetch_port = YoutubeDdakjubu2VideoClient(api_key=settings.youtube_api_key)
    transcript_fetch_port = YoutubeTranscriptApiClient(
        proxy_config=build_proxy_config_from_settings(settings)
    )
    video_summarization_port = OpenAIVideoSummarizationClient(
        api_key=settings.openai_api_key,
        model=settings.ddakjubu2_llm_model,
    )
    video_learning_port = OpenAIVideoLearningClient(
        api_key=settings.openai_api_key,
        model=settings.ddakjubu2_llm_model,
    )
    note_writer_port = Ddakjubu2MarkdownFileWriter(
        file_path=settings.ddakjubu2_enhanced_md_path
    )

    published_after = datetime.fromisoformat(
        settings.ddakjubu2_enhance_published_after_iso
    )

    usecase = EnhanceDdakjubu2VideosUseCase(
        video_fetch_port=video_fetch_port,
        transcript_fetch_port=transcript_fetch_port,
        video_summarization_port=video_summarization_port,
        video_learning_port=video_learning_port,
        note_writer_port=note_writer_port,
        published_after=published_after,
        sleep_between_videos_seconds=settings.ddakjubu2_enhance_sleep_seconds,
        methodology_extraction_port=OpenAIMethodologyExtractionClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
        ),
        note_repository_port=LearningNoteRepositoryImpl(),
        methodology_repository_port=MethodologyRepositoryImpl(),
        llm_model_label=settings.ddakjubu2_llm_model,
    )

    background_tasks.add_task(_run_enhance_in_background, usecase)

    return BaseResponse.ok(
        data={
            "status": "started",
            "file_path": settings.ddakjubu2_enhanced_md_path,
            "sleep_between_videos_seconds": settings.ddakjubu2_enhance_sleep_seconds,
            "published_after": settings.ddakjubu2_enhance_published_after_iso,
        },
        message="딱주부2 자막 포함 재학습이 백그라운드로 시작됐습니다",
    )


async def _run_enhance_in_background(usecase: EnhanceDdakjubu2VideosUseCase) -> None:
    try:
        await usecase.execute()
    except asyncio.CancelledError:
        print("[ddakjubu2_enhance] 백그라운드 작업이 취소됐습니다", flush=True)
        raise
    except Exception as e:
        print(f"[ddakjubu2_enhance] 백그라운드 작업 실패: {e}", flush=True)


# ------------------------------------------------------------------
# 학습 노트 조회 (DB)
# ------------------------------------------------------------------


@router.get("/notes")
async def get_learning_notes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
):
    usecase = GetLearningNotesUseCase(
        note_repository_port=LearningNoteRepositoryImpl()
    )
    response = await usecase.execute(
        limit=limit, offset=offset, date_from=date_from, date_to=date_to
    )
    return BaseResponse.ok(data=response, message="학습 노트 목록 조회 완료")


@router.get("/notes/{video_id}")
async def get_learning_note_detail(video_id: str):
    usecase = GetLearningNoteDetailUseCase(
        note_repository_port=LearningNoteRepositoryImpl(),
        methodology_repository_port=MethodologyRepositoryImpl(),
    )
    response = await usecase.execute(video_id)
    if response is None:
        raise AppException(status_code=404, message="학습 노트를 찾을 수 없습니다.")
    return BaseResponse.ok(data=response, message="학습 노트 상세 조회 완료")


# ------------------------------------------------------------------
# 방법론 (마스터 조회 / 재생성 / 배치 추출)
# ------------------------------------------------------------------


@router.get("/methodology/master")
async def get_master_methodology():
    repository = MethodologyRepositoryImpl()
    master = await repository.find_latest_master()
    if master is None:
        raise AppException(
            status_code=404, message="종합 방법론이 아직 생성되지 않았습니다."
        )
    methodology, version = master
    response = MasterMethodologyResponse(
        version=version, methodology=methodology_to_dto(methodology)
    )
    return BaseResponse.ok(data=response, message="종합 방법론 조회 완료")


@router.post("/methodology/master/rebuild")
async def rebuild_master_methodology(background_tasks: BackgroundTasks):
    settings = get_settings()
    usecase = RebuildMasterMethodologyUseCase(
        methodology_repository_port=MethodologyRepositoryImpl(),
        methodology_merge_port=OpenAIMethodologyMergeClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
        ),
        max_videos=settings.ddakjubu2_master_merge_max_videos,
    )
    background_tasks.add_task(_run_master_rebuild_in_background, usecase)
    return BaseResponse.ok(
        data={"status": "started"},
        message="종합 방법론 재생성이 백그라운드로 시작됐습니다",
    )


async def _run_master_rebuild_in_background(
    usecase: RebuildMasterMethodologyUseCase,
) -> None:
    try:
        await usecase.execute()
    except Exception as e:
        print(f"[ddakjubu2_master] 백그라운드 재생성 실패: {e}", flush=True)


@router.post("/extract-methodologies")
async def extract_methodologies(
    background_tasks: BackgroundTasks,
    max_notes: int = Query(default=100, ge=1, le=1000),
):
    """방법론이 아직 없는 DB 노트들에 대해 방법론 추출을 백그라운드로 배치 실행한다."""
    settings = get_settings()
    usecase = ExtractMethodologiesBatchUseCase(
        note_repository_port=LearningNoteRepositoryImpl(),
        methodology_extraction_port=OpenAIMethodologyExtractionClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
        ),
        methodology_repository_port=MethodologyRepositoryImpl(),
        max_notes=max_notes,
    )
    background_tasks.add_task(
        _run_batch_extraction_in_background, usecase, settings.ddakjubu2_llm_model
    )
    return BaseResponse.ok(
        data={"status": "started", "max_notes": max_notes},
        message="방법론 배치 추출이 백그라운드로 시작됐습니다",
    )


async def _run_batch_extraction_in_background(
    usecase: ExtractMethodologiesBatchUseCase, model_label: str
) -> None:
    try:
        await usecase.execute(model_label=model_label)
    except Exception as e:
        print(f"[ddakjubu2_methodology_batch] 백그라운드 추출 실패: {e}", flush=True)


# ------------------------------------------------------------------
# 백필 (기존 md → DB, 멱등)
# ------------------------------------------------------------------


@router.post("/backfill")
async def backfill_notes_from_markdown():
    settings = get_settings()
    usecase = BackfillNotesFromMarkdownUseCase(
        note_repository_port=LearningNoteRepositoryImpl(),
        sources=[
            (Ddakjubu2MarkdownNoteReader(settings.ddakjubu2_md_path), False),
            (Ddakjubu2MarkdownNoteReader(settings.ddakjubu2_enhanced_md_path), True),
        ],
    )
    response = await usecase.execute()
    return BaseResponse.ok(data=response, message="Markdown → DB 백필 완료")


# ------------------------------------------------------------------
# 방법론 적용 분석
# ------------------------------------------------------------------


@router.post("/apply-analysis")
async def apply_analysis(
    request: ApplyAnalysisRequest,
    redis: aioredis.Redis = Depends(get_redis),
):
    settings = get_settings()
    usecase = ApplyMethodologyUseCase(
        stock_repository=StockRepositoryImpl(),
        methodology_repository_port=MethodologyRepositoryImpl(),
        stock_context_provider_port=StockContextProvider(
            serp_api_key=settings.serp_api_key,
            dart_api_key=settings.open_dart_api_key or settings.dart_api_key,
        ),
        methodology_apply_port=OpenAIMethodologyApplyClient(
            api_key=settings.openai_api_key,
            model=settings.ddakjubu2_llm_model,
            reasoning_effort=settings.ddakjubu2_apply_reasoning_effort,
        ),
        applied_analysis_repository_port=AppliedAnalysisRepositoryImpl(),
        cache_port=RedisAppliedAnalysisCache(redis=redis),
        cache_ttl_seconds=settings.ddakjubu2_apply_cache_ttl_seconds,
    )
    response = await usecase.execute(request)
    return BaseResponse.ok(data=response, message="방법론 적용 분석 완료")


@router.get("/apply-analysis/history")
async def get_apply_analysis_history(
    ticker: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
):
    usecase = GetAppliedAnalysisHistoryUseCase(
        applied_analysis_repository_port=AppliedAnalysisRepositoryImpl()
    )
    items = await usecase.execute(ticker=ticker, limit=limit)
    return BaseResponse.ok(
        data={"items": [item.model_dump() for item in items]},
        message="방법론 적용 분석 이력 조회 완료",
    )
