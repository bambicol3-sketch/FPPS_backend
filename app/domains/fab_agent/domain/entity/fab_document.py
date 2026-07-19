from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

DOC_TYPES = ("SOP", "8D_CAPA", "FA", "MANUAL", "WIKI", "ETC")

# 보안등급: 1=일반, 2=대외비, 3=극비
MIN_GRADE = 1
MAX_GRADE = 3

# 모든 모듈이 볼 수 있는 공용 모듈 식별자
COMMON_MODULE = "COMMON"


@dataclass
class FabChunk:
    chunk_index: int
    text: str
    section_title: Optional[str]
    chunk_hash: str


@dataclass
class FabDocument:
    doc_id: str
    title: str
    doc_type: str
    security_grade: int
    owner_module: str
    source: str
    created_by: str
    created_at: datetime
    chunk_count: int = 0
    chunks: List[FabChunk] = field(default_factory=list)
