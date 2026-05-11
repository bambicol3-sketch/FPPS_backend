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
