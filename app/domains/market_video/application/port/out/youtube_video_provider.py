from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from app.domains.market_video.domain.entity.video_item import VideoItem


@dataclass
class YoutubeVideoSearchResult:
    items: List[VideoItem]
    next_page_token: Optional[str] = None
    prev_page_token: Optional[str] = None
    total_results: int = 0


class YoutubeVideoProvider(ABC):
    @abstractmethod
    async def search(self, page_token: Optional[str] = None) -> YoutubeVideoSearchResult:
        pass
