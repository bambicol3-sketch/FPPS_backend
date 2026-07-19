from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ToolEvidence:
    """도구가 반환한 근거 한 조각. 딱주부 슬라이드의 데이터 provenance 관점을 그대로 반영한다:
    자료가 '어디서 태어나' (data_origin), '누가 수집·검증' (collected_by),
    '어떻게 공개' (publish_method) 되는지를 분리해 기록한다.
    """

    tool: str
    source_institution: str  # 예: SerpAPI/Google Finance, DART, 딱주부TV
    data_origin: str  # 데이터 원천
    collected_by: str  # 수집·검증 주체
    publish_method: str  # 공개 방식
    content: str
    available: bool = True  # 데이터 소스 미연결 시 False
    retrieved_at: Optional[datetime] = None


@dataclass
class ReasoningStep:
    node: str  # planner | researcher | analyst | reviewer
    content: str
    attempt: int = 1


@dataclass
class FrontierAnalysis:
    run_id: str
    question: str
    ticker: Optional[str]
    stock_name: Optional[str]
    plan: str
    answer: str
    confidence: int  # 0-100
    steps: List[ReasoningStep] = field(default_factory=list)
    evidences: List[ToolEvidence] = field(default_factory=list)
    missing_data: List[str] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    revised_count: int = 0
    refused: bool = False
    analyzed_at: Optional[datetime] = None
