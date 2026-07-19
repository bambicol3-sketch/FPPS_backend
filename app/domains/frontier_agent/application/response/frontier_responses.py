from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ToolEvidenceDto(BaseModel):
    tool: str
    source_institution: str
    data_origin: str
    collected_by: str
    publish_method: str
    content: str
    available: bool


class ReasoningStepDto(BaseModel):
    node: str
    content: str
    attempt: int


class FrontierAnalysisResponse(BaseModel):
    run_id: str
    question: str
    ticker: Optional[str] = None
    stock_name: Optional[str] = None
    plan: str
    answer: str
    confidence: int
    steps: List[ReasoningStepDto]
    evidences: List[ToolEvidenceDto]
    missing_data: List[str]
    caveats: List[str]
    revised_count: int
    refused: bool
    analyzed_at: datetime


class FrontierHistoryResponse(BaseModel):
    items: List[FrontierAnalysisResponse]
