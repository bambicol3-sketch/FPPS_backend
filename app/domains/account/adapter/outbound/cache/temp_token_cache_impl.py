import json
from typing import Optional

import redis.asyncio as aioredis

from app.domains.account.application.port.out.temp_token_port import TempTokenPort
from app.domains.account.domain.value_object.temp_token_data import TempTokenData

TEMP_TOKEN_KEY_PREFIX = "temp_token:"


class TempTokenCacheImpl(TempTokenPort):
    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def find_by_token(self, token: str) -> Optional[TempTokenData]:
        raw = await self._redis.get(f"{TEMP_TOKEN_KEY_PREFIX}{token}")
        if not raw:
            return None
        parsed = json.loads(raw)
        provider = parsed.get("provider", "kakao")
        oauth_access_token = (
            parsed.get("oauth_access_token")
            or parsed.get("kakao_access_token")
            or parsed.get("google_access_token")
            or ""
        )
        return TempTokenData(
            oauth_access_token=oauth_access_token,
            nickname=parsed.get("nickname"),
            email=parsed.get("email"),
            provider=provider,
        )

    async def delete_by_token(self, token: str) -> None:
        await self._redis.delete(f"{TEMP_TOKEN_KEY_PREFIX}{token}")
