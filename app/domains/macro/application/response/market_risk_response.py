from datetime import date
from typing import List

from pydantic import BaseModel


class ReferencedVideoItem(BaseModel):
    video_id: str
    title: str
    published_at: str


class MarketRiskResponse(BaseModel):
    as_of: date
    stance: str
    reason_summary: List[str]
    referenced_videos: List[ReferencedVideoItem]
    ddakjubu_md_used: bool
    note: str = ""
