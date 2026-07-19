import re
from typing import Callable, List, Optional

from sqlalchemy import bindparam, delete, select, text

from app.domains.fab_agent.application.port.fab_document_repository_port import (
    FabDocumentRepositoryPort,
)
from app.domains.fab_agent.domain.entity.fab_answer import RetrievedChunk
from app.domains.fab_agent.domain.entity.fab_document import (
    COMMON_MODULE,
    FabChunk,
    FabDocument,
)
from app.domains.fab_agent.infrastructure.orm.fab_document_orm import (
    FabDocumentChunkOrm,
    FabDocumentOrm,
)
from app.infrastructure.database.database import AsyncSessionLocal

TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]{2,}")

VECTOR_SEARCH_SQL = text(
    """
    SELECT c.doc_id, d.title, d.doc_type, c.chunk_index, c.chunk_text,
           c.section_title, c.security_grade, c.owner_module,
           (c.embedding <=> CAST(:emb AS vector)) AS distance
    FROM fab_document_chunks c
    JOIN fab_documents d ON d.doc_id = c.doc_id
    WHERE c.security_grade <= :grade
      AND c.owner_module IN :modules
      AND c.embedding IS NOT NULL
    ORDER BY c.embedding <=> CAST(:emb AS vector)
    LIMIT :k
    """
).bindparams(bindparam("modules", expanding=True))

# 관리자("*") 전용 — 모듈 필터 없이 등급 필터만 적용
VECTOR_SEARCH_SQL_ALL_MODULES = text(
    """
    SELECT c.doc_id, d.title, d.doc_type, c.chunk_index, c.chunk_text,
           c.section_title, c.security_grade, c.owner_module,
           (c.embedding <=> CAST(:emb AS vector)) AS distance
    FROM fab_document_chunks c
    JOIN fab_documents d ON d.doc_id = c.doc_id
    WHERE c.security_grade <= :grade
      AND c.embedding IS NOT NULL
    ORDER BY c.embedding <=> CAST(:emb AS vector)
    LIMIT :k
    """
)

ALL_MODULES = "*"


class FabDocumentRepositoryImpl(FabDocumentRepositoryPort):
    """문서·청크 저장 + 권한 인지(RLS) 하이브리드 검색.

    모든 검색 쿼리는 WHERE 절에서 보안등급·모듈을 사전 필터한다 —
    권한 밖 청크는 애초에 조회되지 않으므로 응답·로그로도 유출되지 않는다.
    """

    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def save_document(
        self,
        document: FabDocument,
        chunks: List[FabChunk],
        embeddings: List[Optional[List[float]]],
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                FabDocumentOrm(
                    doc_id=document.doc_id,
                    title=document.title,
                    doc_type=document.doc_type,
                    security_grade=document.security_grade,
                    owner_module=document.owner_module,
                    source=document.source,
                    chunk_count=len(chunks),
                    created_by=document.created_by,
                )
            )
            await session.flush()  # FK(doc_id) 만족을 위해 문서 먼저 반영
            for chunk, embedding in zip(chunks, embeddings):
                session.add(
                    FabDocumentChunkOrm(
                        doc_id=document.doc_id,
                        chunk_index=chunk.chunk_index,
                        section_title=chunk.section_title,
                        chunk_text=chunk.text,
                        chunk_hash=chunk.chunk_hash,
                        security_grade=document.security_grade,
                        owner_module=document.owner_module,
                        embedding=embedding,
                    )
                )
            await session.commit()

    async def list_documents(
        self, clearance_grade: int, modules: List[str]
    ) -> List[FabDocument]:
        allowed_modules = self._allowed_modules(modules)
        async with self._session_factory() as session:
            stmt = (
                select(FabDocumentOrm)
                .where(FabDocumentOrm.security_grade <= clearance_grade)
                .order_by(FabDocumentOrm.created_at.desc())
            )
            if allowed_modules is not None:
                stmt = stmt.where(FabDocumentOrm.owner_module.in_(allowed_modules))
            rows = (await session.execute(stmt)).scalars().all()
            return [self._to_entity(row) for row in rows]

    async def find_document(self, doc_id: str) -> Optional[FabDocument]:
        async with self._session_factory() as session:
            stmt = select(FabDocumentOrm).where(FabDocumentOrm.doc_id == doc_id)
            row = (await session.execute(stmt)).scalar_one_or_none()
            return self._to_entity(row) if row else None

    async def delete_document(self, doc_id: str) -> bool:
        async with self._session_factory() as session:
            # FK ondelete=CASCADE 로 청크도 함께 삭제 (삭제 전파)
            result = await session.execute(
                delete(FabDocumentOrm).where(FabDocumentOrm.doc_id == doc_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def search_chunks(
        self,
        query_embedding: Optional[List[float]],
        keyword: str,
        clearance_grade: int,
        modules: List[str],
        top_k: int,
    ) -> List[RetrievedChunk]:
        allowed_modules = self._allowed_modules(modules)
        results: List[RetrievedChunk] = []
        seen: set = set()

        if query_embedding is not None:
            vector_hits = await self._vector_search(
                query_embedding, clearance_grade, allowed_modules, top_k
            )
            for hit in vector_hits:
                key = (hit.doc_id, hit.chunk_index)
                if key not in seen:
                    seen.add(key)
                    results.append(hit)

        if len(results) < top_k:
            keyword_hits = await self._keyword_search(
                keyword, clearance_grade, allowed_modules, top_k
            )
            for hit in keyword_hits:
                key = (hit.doc_id, hit.chunk_index)
                if key not in seen and len(results) < top_k:
                    seen.add(key)
                    results.append(hit)

        return results[:top_k]

    async def _vector_search(
        self,
        embedding: List[float],
        clearance_grade: int,
        allowed_modules: Optional[List[str]],
        top_k: int,
    ) -> List[RetrievedChunk]:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        params = {"emb": embedding_str, "grade": clearance_grade, "k": top_k}
        if allowed_modules is None:
            sql = VECTOR_SEARCH_SQL_ALL_MODULES
        else:
            sql = VECTOR_SEARCH_SQL
            params["modules"] = allowed_modules
        async with self._session_factory() as session:
            rows = (await session.execute(sql, params)).all()
        return [
            RetrievedChunk(
                doc_id=row.doc_id,
                title=row.title,
                doc_type=row.doc_type,
                chunk_index=row.chunk_index,
                text=row.chunk_text,
                section_title=row.section_title,
                security_grade=row.security_grade,
                owner_module=row.owner_module,
                score=max(0.0, 1.0 - float(row.distance)),
            )
            for row in rows
        ]

    async def _keyword_search(
        self,
        keyword: str,
        clearance_grade: int,
        allowed_modules: Optional[List[str]],
        top_k: int,
    ) -> List[RetrievedChunk]:
        tokens = sorted(
            set(TOKEN_PATTERN.findall(keyword)), key=len, reverse=True
        )[:4]
        if not tokens:
            return []
        async with self._session_factory() as session:
            stmt = (
                select(FabDocumentChunkOrm, FabDocumentOrm)
                .join(
                    FabDocumentOrm,
                    FabDocumentOrm.doc_id == FabDocumentChunkOrm.doc_id,
                )
                .where(FabDocumentChunkOrm.security_grade <= clearance_grade)
            )
            if allowed_modules is not None:
                stmt = stmt.where(
                    FabDocumentChunkOrm.owner_module.in_(allowed_modules)
                )
            from sqlalchemy import or_

            stmt = stmt.where(
                or_(
                    *[
                        FabDocumentChunkOrm.chunk_text.ilike(f"%{token}%")
                        for token in tokens
                    ]
                )
            ).limit(top_k)
            rows = (await session.execute(stmt)).all()
        return [
            RetrievedChunk(
                doc_id=chunk.doc_id,
                title=doc.title,
                doc_type=doc.doc_type,
                chunk_index=chunk.chunk_index,
                text=chunk.chunk_text,
                section_title=chunk.section_title,
                security_grade=chunk.security_grade,
                owner_module=chunk.owner_module,
                score=0.5,
            )
            for chunk, doc in rows
        ]

    @staticmethod
    def _allowed_modules(modules: List[str]) -> Optional[List[str]]:
        """'*' 포함(관리자) 시 None 반환 → 모듈 필터 미적용. 그 외엔 COMMON 자동 포함."""
        allowed = [m.strip().upper() for m in modules if m.strip()]
        if ALL_MODULES in allowed:
            return None
        if COMMON_MODULE not in allowed:
            allowed.append(COMMON_MODULE)
        return allowed

    @staticmethod
    def _to_entity(row: FabDocumentOrm) -> FabDocument:
        return FabDocument(
            doc_id=row.doc_id,
            title=row.title,
            doc_type=row.doc_type,
            security_grade=row.security_grade,
            owner_module=row.owner_module,
            source=row.source,
            created_by=row.created_by,
            created_at=row.created_at,
            chunk_count=row.chunk_count,
        )
