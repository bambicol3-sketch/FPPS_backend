from abc import ABC, abstractmethod

from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology
from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.domain.entity.source_video import SourceVideo


class MethodologyExtractionPort(ABC):
    """영상에서 재사용 가능한 분석 방법론을 추출하는 포트 (3차 패스)."""

    @abstractmethod
    async def extract(
        self, source_video: SourceVideo, note: LearningNote
    ) -> AnalysisMethodology:
        raise NotImplementedError
