from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base

try:
    from pgvector.sqlalchemy import Vector

    embedding_type = Vector(1536)
except ImportError:  # pgvector 미설치 환경 폴백
    from sqlalchemy import Float
    from sqlalchemy.dialects.postgresql import ARRAY

    embedding_type = ARRAY(Float)


class FabDocumentOrm(Base):
    __tablename__ = "fab_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ETC")
    security_grade: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    owner_module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class FabDocumentChunkOrm(Base):
    __tablename__ = "fab_document_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("fab_documents.doc_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    # RLS 검색 필터용 비정규화 메타 (문서 등급·모듈 상속)
    security_grade: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    owner_module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    embedding = mapped_column(embedding_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
