from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class StockInsightDto(BaseModel):
    stock_name: str
    ticker: str
    investment_view: str
    key_claims: List[str]
    supporting_evidence: List[str]


class MethodologyStepDto(BaseModel):
    step_order: int
    name: str
    description: str
    indicators: List[str]
    decision_rules: List[str]


class MethodologyDto(BaseModel):
    video_id: str
    video_title: str
    methodology_name: str
    analysis_steps: List[MethodologyStepDto]
    indicators_used: List[str]
    decision_rules: List[str]
    risk_management: List[str]
    applicable_market_conditions: str
    example_stocks: List[dict]
    extracted_at: datetime


class MasterMethodologyResponse(BaseModel):
    version: int
    methodology: MethodologyDto


class LearningNoteListItem(BaseModel):
    video_id: str
    video_title: str
    program_category: str
    published_at: datetime
    summary_preview: str
    stock_names: List[str]
    has_transcript: bool
    has_methodology: bool


class LearningNoteListResponse(BaseModel):
    items: List[LearningNoteListItem]
    total: int
    limit: int
    offset: int


class LearningNoteDetailResponse(BaseModel):
    video_id: str
    video_title: str
    channel_name: str
    program_category: str
    published_at: datetime
    learned_at: datetime
    summary: str
    stock_insights: List[StockInsightDto]
    methodology: Optional[MethodologyDto] = None


class BackfillResponse(BaseModel):
    parsed_count: int
    inserted_count: int
    skipped_existing_count: int
    failed_count: int
    source_files: List[str]
