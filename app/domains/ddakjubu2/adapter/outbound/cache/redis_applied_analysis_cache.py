import logging
from typing import Optional

import redis.asyncio as aioredis

from app.domains.ddakjubu2.application.port.applied_analysis_cache_port import (
    AppliedAnalysisCachePort,
)
from app.domains.ddakjubu2.application.response.applied_analysis_response import (
    AppliedAnalysisResponse,
)

logger = logging.getLogger(__name__)


class RedisAppliedAnalysisCache(AppliedAnalysisCachePort):
    """방법론 적용 분석 결과의 Redis 캐시."""

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def get(self, key: str) -> Optional[AppliedAnalysisResponse]:
        try:
            raw = await self._redis.get(key)
        except aioredis.RedisError as e:
            logger.warning("[ddakjubu2_apply_cache] Redis get 실패: %s", e)
            return None
        if raw is None:
            return None
        try:
            return AppliedAnalysisResponse.model_validate_json(raw)
        except Exception as e:
            logger.warning("[ddakjubu2_apply_cache] 캐시 역직렬화 실패: %s", e)
            return None

    async def save(
        self, key: str, response: AppliedAnalysisResponse, ttl_seconds: int
    ) -> None:
        try:
            await self._redis.setex(key, ttl_seconds, response.model_dump_json())
        except aioredis.RedisError as e:
            logger.warning("[ddakjubu2_apply_cache] Redis setex 실패: %s", e)
        except Exception as e:
            logger.warning("[ddakjubu2_apply_cache] 캐시 직렬화 실패: %s", e)
