import uuid
from datetime import datetime, timezone
from typing import List

from app.common.exception.app_exception import AppException
from app.domains.disclosure.domain.service.text_chunker import TextChunker
from app.domains.fab_agent.application.port.fab_document_repository_port import (
    FabDocumentRepositoryPort,
)
from app.domains.fab_agent.application.port.fab_llm_ports import FabEmbeddingPort
from app.domains.fab_agent.application.request.fab_requests import (
    IngestDocumentRequest,
)
from app.domains.fab_agent.application.response.fab_responses import (
    FabDocumentSummaryDto,
    IngestDocumentResponse,
)
from app.domains.fab_agent.domain.entity.fab_document import (
    DOC_TYPES,
    FabChunk,
    FabDocument,
)
from app.domains.fab_agent.domain.entity.fab_user_access import FabUserAccess


def document_to_dto(document: FabDocument) -> FabDocumentSummaryDto:
    return FabDocumentSummaryDto(
        doc_id=document.doc_id,
        title=document.title,
        doc_type=document.doc_type,
        security_grade=document.security_grade,
        owner_module=document.owner_module,
        source=document.source,
        chunk_count=document.chunk_count,
        created_by=document.created_by,
        created_at=document.created_at,
    )


class IngestDocumentUseCase:
    """텍스트/마크다운 문서를 청킹·임베딩해 보안등급·모듈 메타와 함께 인덱싱한다."""

    def __init__(
        self,
        document_repository_port: FabDocumentRepositoryPort,
        embedding_port: FabEmbeddingPort,
    ):
        self._document_repository_port = document_repository_port
        self._embedding_port = embedding_port
        self._chunker = TextChunker()

    async def execute(
        self, access: FabUserAccess, request: IngestDocumentRequest
    ) -> IngestDocumentResponse:
        if not access.is_admin:
            raise AppException(status_code=403, message="문서 등록은 관리자만 가능합니다.")

        doc_type = request.doc_type.upper()
        if doc_type not in DOC_TYPES:
            doc_type = "ETC"

        raw_chunks = self._chunker.chunk_text(request.content)
        if not raw_chunks:
            raise AppException(status_code=400, message="본문에서 청크를 만들 수 없습니다.")

        chunks = [
            FabChunk(
                chunk_index=c["chunk_index"],
                text=c["chunk_text"],
                section_title=c.get("section_title"),
                chunk_hash=c["chunk_hash"],
            )
            for c in raw_chunks
        ]

        try:
            embeddings = await self._embedding_port.embed_batch(
                [c.text for c in chunks]
            )
        except Exception as e:
            print(f"[fab_agent] 임베딩 실패(키워드 검색 전용으로 저장) error={e}", flush=True)
            embeddings = [None] * len(chunks)

        document = FabDocument(
            doc_id=uuid.uuid4().hex,
            title=request.title.strip(),
            doc_type=doc_type,
            security_grade=request.security_grade,
            owner_module=request.owner_module.strip().upper(),
            source=request.source,
            created_by=access.account_email,
            created_at=datetime.now(timezone.utc),
            chunk_count=len(chunks),
        )
        await self._document_repository_port.save_document(
            document, chunks, embeddings
        )
        print(
            f"[fab_agent] 문서 인덱싱 완료 doc_id={document.doc_id} "
            f"grade={document.security_grade} module={document.owner_module} "
            f"chunks={len(chunks)}",
            flush=True,
        )
        return IngestDocumentResponse(
            doc_id=document.doc_id, chunk_count=len(chunks)
        )


class ListDocumentsUseCase:
    def __init__(self, document_repository_port: FabDocumentRepositoryPort):
        self._document_repository_port = document_repository_port

    async def execute(self, access: FabUserAccess) -> List[FabDocumentSummaryDto]:
        documents = await self._document_repository_port.list_documents(
            clearance_grade=access.clearance_grade, modules=access.modules
        )
        return [document_to_dto(d) for d in documents]


class DeleteDocumentUseCase:
    def __init__(self, document_repository_port: FabDocumentRepositoryPort):
        self._document_repository_port = document_repository_port

    async def execute(self, access: FabUserAccess, doc_id: str) -> None:
        if not access.is_admin:
            raise AppException(status_code=403, message="문서 삭제는 관리자만 가능합니다.")
        deleted = await self._document_repository_port.delete_document(doc_id)
        if not deleted:
            raise AppException(status_code=404, message="문서를 찾을 수 없습니다.")
