import redis.asyncio as aioredis
from fastapi import APIRouter, Depends

from app.common.response.base_response import BaseResponse
from app.domains.macro.adapter.outbound.cache.redis_market_risk_cache import (
    RedisMarketRiskCache,
)
from app.domains.macro.adapter.outbound.external.openai_market_risk_client import (
    OpenAIMarketRiskClient,
)
from app.domains.macro.adapter.outbound.external.youtube_recent_video_client import (
    YoutubeRecentVideoClient,
)
from app.domains.macro.adapter.outbound.external.youtube_transcript_client import (
    YoutubeTranscriptClient,
)
from app.domains.macro.adapter.outbound.persistence.ddakjubu_file_reader import (
    LocalDdakjubuFileReader,
)
from app.domains.macro.application.usecase.assess_market_risk_usecase import (
    AssessMarketRiskUseCase,
)
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/market-risk")
async def assess_market_risk(
    redis: aioredis.Redis = Depends(get_redis),
):
    settings = get_settings()

    file_reader = LocalDdakjubuFileReader(file_path=settings.ddakjubu_md_path)
    video_fetch_port = YoutubeRecentVideoClient(api_key=settings.youtube_api_key)
    transcript_port = YoutubeTranscriptClient()
    llm_port = OpenAIMarketRiskClient(
        api_key=settings.openai_api_key,
        model=settings.ddakjubu_llm_model,
    )
    cache_port = RedisMarketRiskCache(redis=redis)

    usecase = AssessMarketRiskUseCase(
        ddakjubu_file_reader_port=file_reader,
        video_fetch_port=video_fetch_port,
        transcript_fetch_port=transcript_port,
        market_risk_llm_port=llm_port,
        cache_port=cache_port,
    )
    response = await usecase.execute()

    return BaseResponse.ok(data=response, message="오늘 기준 시장 Risk 판단 완료")
