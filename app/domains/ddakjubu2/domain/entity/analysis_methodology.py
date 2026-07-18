from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class MethodologyStep:
    step_order: int
    name: str
    description: str
    indicators: List[str] = field(default_factory=list)
    decision_rules: List[str] = field(default_factory=list)


@dataclass
class MethodologyExample:
    stock_name: str
    ticker: str
    applied_view: str


@dataclass
class AnalysisMethodology:
    """영상에서 역설계한 '재사용 가능한 분석 방법론'.

    video_id 가 빈 문자열이면 여러 영상을 통합한 마스터 방법론이다.
    """

    video_id: str
    video_title: str
    methodology_name: str
    analysis_steps: List[MethodologyStep]
    indicators_used: List[str]
    decision_rules: List[str]
    risk_management: List[str]
    applicable_market_conditions: str
    example_stocks: List[MethodologyExample]
    extracted_at: datetime

    def is_empty(self) -> bool:
        return not self.analysis_steps
