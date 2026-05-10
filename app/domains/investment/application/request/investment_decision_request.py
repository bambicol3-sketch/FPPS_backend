from pydantic import BaseModel, Field


class InvestmentDecisionRequest(BaseModel):
    """투자 판단 요청 — 사용자의 질의 텍스트."""

    query: str = Field(..., min_length=1, description="투자 관련 질문")
