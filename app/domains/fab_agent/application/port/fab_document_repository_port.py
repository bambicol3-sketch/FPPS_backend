from abc import ABC, abstractmethod
from typing import List, Optional

from app.domains.fab_agent.domain.entity.fab_answer import RetrievedChunk
from app.domains.fab_agent.domain.entity.fab_document import FabChunk, FabDocument


class FabDocumentRepositoryPort(ABC):
    """문서·청크 저장 및 권한 인지 검색 포트.

    search_chunks 는 반드시 clearance_grade / modules 로 사전 필터(RLS)한다.
    """

    @abstractmethod
    async def save_document(
        self,
        document: FabDocument,
        chunks: List[FabChunk],
        embeddings: List[Optional[List[float]]],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_documents(
        self, clearance_grade: int, modules: List[str]
    ) -> List[FabDocument]:
        raise NotImplementedError

    @abstractmethod
    async def find_document(self, doc_id: str) -> Optional[FabDocument]:
        raise NotImplementedError

    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def search_chunks(
        self,
        query_embedding: Optional[List[float]],
        keyword: str,
        clearance_grade: int,
        modules: List[str],
        top_k: int,
    ) -> List[RetrievedChunk]:
        raise NotImplementedError
