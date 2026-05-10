from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from app.domains.macro.domain.entity.reference_video import ReferenceVideo


class MacroVideoFetchPort(ABC):
    """매크로 판단용 채널 영상 조회 포트."""

    @abstractmethod
    async def fetch_recent_videos(
        self,
        channel_ids: List[str],
        published_after: datetime,
        max_per_channel: int = 20,
    ) -> List[ReferenceVideo]:
        """channel_ids가 비어있거나 영상이 없으면 빈 리스트를 반환한다."""
        raise NotImplementedError
