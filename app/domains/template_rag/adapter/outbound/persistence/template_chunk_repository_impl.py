import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.template_rag.application.port.template_chunk_repository_port import (
    TemplateChunkRepositoryPort,
)
from app.domains.template_rag.domain.entity.template_chunk import TemplateChunk
from app.domains.template_rag.infrastructure.mapper.template_chunk_mapper import (
    TemplateChunkMapper,
)
from app.domains.template_rag.infrastructure.orm.template_chunk_orm import (
    TemplateChunkOrm,
)

logger = logging.getLogger(__name__)


class TemplateChunkRepositoryImpl(TemplateChunkRepositoryPort):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_file_hash(
        self, form_type: str, file_path: str
    ) -> Optional[str]:
        stmt = (
            select(TemplateChunkOrm.file_hash)
            .where(TemplateChunkOrm.form_type == form_type)
            .where(TemplateChunkOrm.file_path == file_path)
            .limit(1)
        )
        result = await self._db.execute(stmt)
        row = result.first()
        return row[0] if row else None

    async def delete_by_file(self, form_type: str, file_path: str) -> int:
        stmt = (
            delete(TemplateChunkOrm)
            .where(TemplateChunkOrm.form_type == form_type)
            .where(TemplateChunkOrm.file_path == file_path)
        )
        result = await self._db.execute(stmt)
        await self._db.commit()
        return result.rowcount or 0

    async def upsert_bulk(self, chunks: list[TemplateChunk]) -> int:
        if not chunks:
            return 0
        now = datetime.now()
        values_list = [
            {
                "form_type": c.form_type,
                "file_path": c.file_path,
                "file_name": c.file_name,
                "file_hash": c.file_hash,
                "chunk_index": c.chunk_index,
                "chunk_text": c.chunk_text,
                "chunk_hash": c.chunk_hash,
                "embedding": c.embedding,
                "created_at": now,
                "updated_at": now,
            }
            for c in chunks
        ]

        stmt = insert(TemplateChunkOrm).values(values_list)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_template_chunks_sheet_file_idx",
            set_={
                "chunk_text": stmt.excluded.chunk_text,
                "chunk_hash": stmt.excluded.chunk_hash,
                "embedding": stmt.excluded.embedding,
                "file_hash": stmt.excluded.file_hash,
                "file_name": stmt.excluded.file_name,
                "updated_at": now,
            },
        )

        result = await self._db.execute(stmt)
        await self._db.commit()
        affected = result.rowcount if result.rowcount and result.rowcount > 0 else len(chunks)
        logger.info(
            "[TemplateRAG] upsert form_type=%s rows=%d", chunks[0].form_type, affected
        )
        return affected

    async def count_by_form_type(self, form_type: str) -> int:
        stmt = select(func.count()).select_from(TemplateChunkOrm).where(
            TemplateChunkOrm.form_type == form_type
        )
        result = await self._db.execute(stmt)
        return int(result.scalar() or 0)

    async def find_template_pptx_path(
        self,
        form_type: str,
        exclude_dir: Optional[str] = None,
    ) -> Optional[str]:
        stmt = (
            select(TemplateChunkOrm.file_path)
            .where(TemplateChunkOrm.form_type == form_type)
            .where(TemplateChunkOrm.file_path.ilike("%.pptx"))
            .distinct()
        )
        if exclude_dir:
            normalized = exclude_dir.rstrip("/") + "/"
            stmt = stmt.where(~TemplateChunkOrm.file_path.startswith(normalized))
        result = await self._db.execute(stmt)
        paths = [row[0] for row in result.all()]
        if not paths:
            return None

        # '양식' / 'template' / 'form' 키워드 우선
        keywords = ("양식", "template", "form", "Template", "Form")
        for kw in keywords:
            for p in paths:
                if kw in p:
                    return p
        return paths[0]

    async def list_by_form_type(
        self, form_type: str, limit: Optional[int] = None
    ) -> list[TemplateChunk]:
        stmt = (
            select(TemplateChunkOrm)
            .where(TemplateChunkOrm.form_type == form_type)
            .order_by(TemplateChunkOrm.file_path, TemplateChunkOrm.chunk_index)
        )
        if limit is not None and limit > 0:
            stmt = stmt.limit(limit)
        result = await self._db.execute(stmt)
        return [
            TemplateChunkMapper.to_entity(orm) for orm in result.scalars().all()
        ]

    async def identify_best_form_type(
        self, embedding: list[float]
    ) -> Optional[tuple[str, float]]:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        query = text(
            """
            SELECT form_type, MIN(embedding <=> CAST(:embedding AS vector)) AS dist
            FROM template_chunks
            WHERE embedding IS NOT NULL
            GROUP BY form_type
            ORDER BY dist ASC
            LIMIT 1
            """
        )
        try:
            result = await self._db.execute(query, {"embedding": embedding_str})
            row = result.first()
        except Exception as e:
            logger.warning("[TemplateRAG] identify_best_form_type failed: %s", e)
            return None
        if row is None:
            return None
        return (row.form_type, float(row.dist))

    async def search_similar(
        self,
        form_type: str,
        embedding: list[float],
        limit: int = 10,
    ) -> list[TemplateChunk]:
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        query = text(
            """
            SELECT id, form_type, file_path, file_name, file_hash, chunk_index,
                   chunk_text, chunk_hash, embedding, created_at, updated_at
            FROM template_chunks
            WHERE form_type = :form_type
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
            """
        )

        try:
            result = await self._db.execute(
                query,
                {
                    "form_type": form_type,
                    "embedding": embedding_str,
                    "limit": limit,
                },
            )
            rows = result.fetchall()
        except Exception as e:
            logger.warning(
                "[TemplateRAG] vector search failed (form_type=%s): %s",
                form_type,
                e,
            )
            return []

        return [
            TemplateChunk(
                id=row.id,
                form_type=row.form_type,
                file_path=row.file_path,
                file_name=row.file_name,
                file_hash=row.file_hash,
                chunk_index=row.chunk_index,
                chunk_text=row.chunk_text,
                chunk_hash=row.chunk_hash,
                embedding=list(row.embedding) if row.embedding is not None else None,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
