from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class AppliedAnalysisOrm(Base):
    __tablename__ = "ddakjubu2_applied_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    stock_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    video_id: Mapped[str] = mapped_column(String(50), nullable=True)
    overall_view: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
