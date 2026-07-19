from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    # 종목명(한글) 또는 6자리 코드. 없으면 종목 비특정 질문으로 처리.
    stock_input: Optional[str] = Field(default=None, max_length=50)
