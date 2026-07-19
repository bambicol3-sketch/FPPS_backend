from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RetrievedChunk:
    """권한 필터를 통과해 검색된 청크 (인용 후보)."""

    doc_id: str
    title: str
    doc_type: str
    chunk_index: int
    text: str
    section_title: Optional[str]
    security_grade: int
    owner_module: str
    score: float


@dataclass
class FabCitation:
    ref_number: int
    doc_id: str
    title: str
    chunk_index: int
    quote: str
    security_grade: int
    owner_module: str


@dataclass
class FabAnswer:
    answer: str
    citations: List[FabCitation] = field(default_factory=list)
    used_grade_max: int = 0
    refused: bool = False
    refusal_reason: str = ""
