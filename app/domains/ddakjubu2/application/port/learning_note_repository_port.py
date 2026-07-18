from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Tuple

from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote


@dataclass
class LearningNoteSummaryData:
    """목록 조회용 요약 데이터 (방법론 보유 여부 포함)."""

    video_id: str
    video_title: str
    program_category: str
    published_at: datetime
    summary: str
    stock_names: List[str]
    has_transcript: bool
    has_methodology: bool


class LearningNoteRepositoryPort(ABC):
    """학습 노트 DB 저장/조회 포트."""

    @abstractmethod
    async def save_note(
        self, note: LearningNote, has_transcript: bool, source: str
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, video_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def find_notes(
        self,
        limit: int,
        offset: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Tuple[List[LearningNoteSummaryData], int]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_video_id(self, video_id: str) -> Optional[LearningNote]:
        raise NotImplementedError

    @abstractmethod
    async def find_video_ids_without_methodology(self, limit: int) -> List[str]:
        raise NotImplementedError
