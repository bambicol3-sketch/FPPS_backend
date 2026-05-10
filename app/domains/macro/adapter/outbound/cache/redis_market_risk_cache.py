import json
import logging
from datetime import date
from typing import Optional

import redis.asyncio as aioredis

from app.domains.macro.application.port.market_risk_cache_port import MarketRiskCachePort
from app.domains.macro.application.response.market_risk_response import MarketRiskResponse

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "macro:market-risk:"


class RedisMarketRiskCache(MarketRiskCachePort):
    """Redis 기반 일자별 매크로 판단 결과 캐시."""

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def get(self, as_of: date) -> Optional[MarketRiskResponse]:
        key = self._key(as_of)
        try:
            raw = await self._redis.get(key)
        except aioredis.RedisError as e:
            logger.warning("[macro_cache] Redis get 실패: %s", e)
            return None
        if raw is None:
            return None
        try:
            return MarketRiskResponse.model_validate_json(raw)
        except Exception as e:
            logger.warning("[macro_cache] 캐시 역직렬화 실패: %s", e)
            return None

    async def save(
        self,
        as_of: date,
        response: MarketRiskResponse,
        ttl_seconds: int,
    ) -> None:
        key = self._key(as_of)
        try:
            payload = response.model_dump_json()
            await self._redis.setex(key, ttl_seconds, payload)
        except aioredis.RedisError as e:
            logger.warning("[macro_cache] Redis setex 실패: %s", e)
        except Exception as e:
            logger.warning("[macro_cache] 캐시 직렬화 실패: %s", e)

    @staticmethod
    def _key(as_of: date) -> str:
        return f"{CACHE_KEY_PREFIX}{as_of.strftime('%Y-%m-%d')}"
