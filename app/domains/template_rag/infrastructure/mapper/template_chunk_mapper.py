from app.domains.template_rag.domain.entity.template_chunk import TemplateChunk
from app.domains.template_rag.infrastructure.orm.template_chunk_orm import (
    TemplateChunkOrm,
)


class TemplateChunkMapper:
    @staticmethod
    def to_entity(orm: TemplateChunkOrm) -> TemplateChunk:
        return TemplateChunk(
            id=orm.id,
            form_type=orm.form_type,
            file_path=orm.file_path,
            file_name=orm.file_name,
            file_hash=orm.file_hash,
            chunk_index=orm.chunk_index,
            chunk_text=orm.chunk_text,
            chunk_hash=orm.chunk_hash,
            embedding=list(orm.embedding) if orm.embedding is not None else None,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
