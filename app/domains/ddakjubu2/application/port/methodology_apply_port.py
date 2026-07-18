from abc import ABC, abstractmethod

from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology
from app.domains.ddakjubu2.domain.entity.applied_analysis import AppliedAnalysis


class MethodologyApplyPort(ABC):
    """방법론을 대상 종목 데이터에 적용해 단계별 분석을 생성하는 포트."""

    @abstractmethod
    async def apply(
        self,
        methodology: AnalysisMethodology,
        stock_context: str,
        stock_name: str,
        ticker: str,
    ) -> AppliedAnalysis:
        raise NotImplementedError
