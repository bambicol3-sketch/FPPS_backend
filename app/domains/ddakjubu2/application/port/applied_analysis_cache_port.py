from abc import ABC, abstractmethod
from typing import Optional

from app.domains.ddakjubu2.application.response.applied_analysis_response import (
    AppliedAnalysisResponse,
)


class AppliedAnalysisCachePort(ABC):
    """방법론 적용 분석 결과 캐시 포트."""

    @abstractmethod
    async def get(self, key: str) -> Optional[AppliedAnalysisResponse]:
        raise NotImplementedError

    @abstractmethod
    async def save(
        self, key: str, response: AppliedAnalysisResponse, ttl_seconds: int
    ) -> None:
        raise NotImplementedError
