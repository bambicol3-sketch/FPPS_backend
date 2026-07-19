from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class FabCitationDto(BaseModel):
    ref_number: int
    doc_id: str
    title: str
    chunk_index: int
    quote: str
    security_grade: int
    owner_module: str


class AskResponse(BaseModel):
    request_id: str
    session_id: str
    answer: str
    citations: List[FabCitationDto]
    used_grade_max: int
    refused: bool
    refusal_reason: str = ""


class FabDocumentSummaryDto(BaseModel):
    doc_id: str
    title: str
    doc_type: str
    security_grade: int
    owner_module: str
    source: str
    chunk_count: int
    created_by: str
    created_at: datetime


class IngestDocumentResponse(BaseModel):
    doc_id: str
    chunk_count: int


class FabAccessDto(BaseModel):
    account_email: str
    clearance_grade: int
    modules: List[str]
    is_admin: bool


class FabAuditEntryDto(BaseModel):
    request_id: str
    account_email: str
    session_id: str
    question: str
    answer: str
    used_grade_max: int
    refused: bool
    latency_ms: int
    created_at: datetime


class FabChatMessageDto(BaseModel):
    role: str
    content: str
    citations: Optional[List[dict]] = None
    created_at: datetime
