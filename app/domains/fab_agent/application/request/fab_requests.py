from typing import List, Optional

from pydantic import BaseModel, Field


class IngestDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    doc_type: str = Field(default="ETC", max_length=20)
    security_grade: int = Field(ge=1, le=3)
    owner_module: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=10)
    source: str = Field(default="manual-upload", max_length=100)


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    session_id: Optional[str] = Field(default=None, max_length=64)


class UpsertAccessRequest(BaseModel):
    account_email: str = Field(min_length=3, max_length=255)
    clearance_grade: int = Field(ge=1, le=3)
    modules: List[str] = Field(default_factory=list)
    is_admin: bool = False


class FeedbackRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)
    rating: str = Field(pattern="^(up|down)$")
    reason: Optional[str] = Field(default=None, max_length=1000)
