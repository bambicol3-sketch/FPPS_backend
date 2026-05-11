from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base

try:
    from pgvector.sqlalchemy import Vector

    embedding_type = Vector(1536)
except ImportError:
    from sqlalchemy import Float
    from sqlalchemy.dialects.postgresql import ARRAY

    embedding_type = ARRAY(Float)


class TemplateChunkOrm(Base):
    __tablename__ = "template_chunks"
    __table_args__ = (
        UniqueConstraint(
            "form_type",
            "file_path",
            "chunk_index",
            name="uq_template_chunks_sheet_file_idx",
        ),
        Index("ix_template_chunks_form_type", "form_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    form_type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding = mapped_column(embedding_type, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )
