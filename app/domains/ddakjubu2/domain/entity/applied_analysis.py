from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class AppliedStepResult:
    step_order: int
    step_name: str
    data_used: str
    assessment: str
    view_contribution: str


@dataclass
class AppliedAnalysis:
    """딱주부 방법론을 임의 종목에 적용한 분석 결과."""

    ticker: str
    stock_name: str
    mode: str  # "per_video" | "master"
    video_id: Optional[str]
    methodology_name: str
    overall_view: str  # 강세 | 약세 | 중립 | 관망
    confidence: int  # 0-100
    step_results: List[AppliedStepResult]
    missing_data: List[str]
    caveats: List[str]
    summary: str
    analyzed_at: datetime
    master_version: Optional[int] = field(default=None)
