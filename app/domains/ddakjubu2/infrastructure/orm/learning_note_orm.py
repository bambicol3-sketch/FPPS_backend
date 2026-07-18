from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class LearningNoteOrm(Base):
    __tablename__ = "ddakjubu2_learning_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    video_title: Mapped[str] = mapped_column(Text, nullable=False)
    channel_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    program_category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="전체영상"
    )
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    learned_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    stock_insights: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    has_transcript: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
