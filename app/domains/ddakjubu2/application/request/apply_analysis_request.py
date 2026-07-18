from typing import Literal, Optional

from pydantic import BaseModel, Field


class ApplyAnalysisRequest(BaseModel):
    """방법론 적용 분석 요청.

    stock_input: 종목명(한글) 또는 6자리 종목 코드
    mode: per_video (특정 방송의 방법론) | master (종합 방법론)
    video_id: mode=per_video 일 때 필수
    """

    stock_input: str = Field(min_length=1, max_length=50)
    mode: Literal["per_video", "master"] = "master"
    video_id: Optional[str] = None
