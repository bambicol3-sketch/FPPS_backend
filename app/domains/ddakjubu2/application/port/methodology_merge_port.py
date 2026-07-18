from abc import ABC, abstractmethod
from typing import List

from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology


class MethodologyMergePort(ABC):
    """여러 영상의 방법론을 하나의 마스터(종합) 방법론으로 통합하는 포트."""

    @abstractmethod
    async def merge(
        self, methodologies: List[AnalysisMethodology]
    ) -> AnalysisMethodology:
        raise NotImplementedError
