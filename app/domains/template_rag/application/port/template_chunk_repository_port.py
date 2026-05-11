from abc import ABC, abstractmethod
from typing import Optional

from app.domains.template_rag.domain.entity.template_chunk import TemplateChunk


class TemplateChunkRepositoryPort(ABC):
    @abstractmethod
    async def get_file_hash(self, form_type: str, file_path: str) -> Optional[str]: ...

    @abstractmethod
    async def delete_by_file(self, form_type: str, file_path: str) -> int: ...

    @abstractmethod
    async def upsert_bulk(self, chunks: list[TemplateChunk]) -> int: ...

    @abstractmethod
    async def count_by_form_type(self, form_type: str) -> int: ...

    @abstractmethod
    async def search_similar(
        self,
        form_type: str,
        embedding: list[float],
        limit: int = 10,
    ) -> list[TemplateChunk]: ...
