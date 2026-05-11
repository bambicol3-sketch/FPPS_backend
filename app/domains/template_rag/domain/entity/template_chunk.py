from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TemplateChunk:
    form_type: str
    file_path: str
    file_name: str
    file_hash: str
    chunk_index: int
    chunk_text: str
    chunk_hash: str
    embedding: Optional[list[float]] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
