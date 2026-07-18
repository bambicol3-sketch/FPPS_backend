from abc import ABC, abstractmethod
from typing import List, Optional

from app.domains.ddakjubu2.domain.entity.applied_analysis import AppliedAnalysis


class AppliedAnalysisRepositoryPort(ABC):
    """방법론 적용 분석 결과 저장/이력 조회 포트."""

    @abstractmethod
    async def save(self, analysis: AppliedAnalysis) -> None:
        raise NotImplementedError

    @abstractmethod
    async def find_history(
        self, ticker: Optional[str], limit: int
    ) -> List[AppliedAnalysis]:
        raise NotImplementedError
