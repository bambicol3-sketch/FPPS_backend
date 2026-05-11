from typing import Optional

from pydantic import BaseModel, Field


class IngestTemplatesRequest(BaseModel):
    base_dir: Optional[str] = Field(
        default=None,
        description="양식 폴더들이 모여있는 베이스 디렉토리. 미지정 시 overrides 필수.",
    )
    overrides: dict[str, str] = Field(
        default_factory=dict,
        description="양식별 폴더 경로 오버라이드. key=FormType 문자열(FRS, Strategy, ...).",
    )
