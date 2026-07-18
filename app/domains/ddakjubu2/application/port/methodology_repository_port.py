from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology


class MethodologyRepositoryPort(ABC):
    """영상별 방법론 및 마스터(종합) 방법론 저장/조회 포트."""

    @abstractmethod
    async def save(self, methodology: AnalysisMethodology, model: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, video_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def find_by_video_id(self, video_id: str) -> Optional[AnalysisMethodology]:
        raise NotImplementedError

    @abstractmethod
    async def find_recent(self, limit: int) -> List[AnalysisMethodology]:
        raise NotImplementedError

    @abstractmethod
    async def save_master(
        self, methodology: AnalysisMethodology, source_video_count: int
    ) -> int:
        """마스터 방법론을 새 버전으로 저장하고 버전 번호를 반환한다."""
        raise NotImplementedError

    @abstractmethod
    async def find_latest_master(
        self,
    ) -> Optional[Tuple[AnalysisMethodology, int]]:
        """(마스터 방법론, 버전) 을 반환한다. 없으면 None."""
        raise NotImplementedError
