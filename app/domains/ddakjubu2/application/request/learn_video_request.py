from typing import Optional

from pydantic import BaseModel, Field


class LearnVideoRequest(BaseModel):
    """단건 영상 학습 요청.

    video_input: YouTube URL 또는 11자 video_id (노트 식별자로 항상 필요)
    transcript / title / description: 직접 붙여넣기 (선택).
      제공되면 YouTube Data API·자막 스크래핑을 건너뛰고 이 내용으로 학습한다.
      라이브 다시보기(자막 미생성)·폐쇄망·API 키 미설정 환경에서 유용하다.
    """

    video_input: str = Field(min_length=5, max_length=300)
    title: Optional[str] = Field(default=None, max_length=300)
    transcript: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None, max_length=5000)
