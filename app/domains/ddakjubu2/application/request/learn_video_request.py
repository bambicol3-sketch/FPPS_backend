from pydantic import BaseModel, Field


class LearnVideoRequest(BaseModel):
    """단건 영상 학습 요청. video_input: YouTube URL 또는 11자 video_id."""

    video_input: str = Field(min_length=5, max_length=300)
