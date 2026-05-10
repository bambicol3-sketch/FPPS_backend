from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from app.domains.macro.application.response.market_risk_response import MarketRiskResponse


class MarketRiskCachePort(ABC):
    """오늘의 매크로 Risk 판단 결과 캐시 포트."""

    @abstractmethod
    async def get(self, as_of: date) -> Optional[MarketRiskResponse]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, as_of: date, response: MarketRiskResponse, ttl_seconds: int) -> None:
        raise NotImplementedError
