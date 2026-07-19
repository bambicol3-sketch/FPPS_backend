from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.database import Base


class FrontierAnalysisRunOrm(Base):
    __tablename__ = "frontier_analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    stock_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)  # 전체 트레이스·근거
    revised_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class FrontierAuditLogOrm(Base):
    """불변 감사 로그 — INSERT/SELECT 만."""

    __tablename__ = "frontier_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(20), nullable=True)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tools_used: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    revised_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    refused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, index=True
    )
