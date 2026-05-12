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

    @abstractmethod
    async def identify_best_form_type(
        self, embedding: list[float]
    ) -> Optional[tuple[str, float]]:
        """주어진 embedding 에 가장 가까운 청크를 가진 form_type 과 거리(작을수록 유사)."""

    @abstractmethod
    async def list_by_form_type(
        self, form_type: str, limit: Optional[int] = None
    ) -> list[TemplateChunk]:
        """양식별 저장된 청크 목록을 chunk_index 오름차순으로 반환."""

    @abstractmethod
    async def find_template_pptx_path(
        self,
        form_type: str,
        exclude_dir: Optional[str] = None,
    ) -> Optional[str]:
        """해당 양식 sheet 에 ingest 된 .pptx 파일 경로 한 개 반환.

        - exclude_dir 가 주어지면 그 디렉토리 하위 파일은 제외 (raw data 와 분리)
        - 파일명/경로에 '양식'/'template'/'form' 키워드 있는 걸 우선
        """
