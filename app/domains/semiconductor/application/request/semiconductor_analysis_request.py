from pydantic import BaseModel, Field


class SemiconductorAnalysisRequest(BaseModel):
    ticker: str = Field(..., description="종목 코드 (예: 005930)", min_length=1)
    query: str | None = Field(
        default=None,
        description="분석 질의 (미입력 시 기본 시황 분석 수행)",
    )
