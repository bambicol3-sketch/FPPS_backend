from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AppliedStepResultDto(BaseModel):
    step_order: int
    step_name: str
    data_used: str
    assessment: str
    view_contribution: str


class AppliedAnalysisResponse(BaseModel):
    ticker: str
    stock_name: str
    mode: str
    video_id: Optional[str] = None
    master_version: Optional[int] = None
    methodology_name: str
    overall_view: str
    confidence: int
    step_results: List[AppliedStepResultDto]
    missing_data: List[str]
    caveats: List[str]
    summary: str
    analyzed_at: datetime
    cached: bool = False


class AppliedAnalysisHistoryResponse(BaseModel):
    items: List[AppliedAnalysisResponse]
