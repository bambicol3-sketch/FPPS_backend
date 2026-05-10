from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.vector_database import VectorBase


class InterestArticleContentOrm(VectorBase):
    """관심 기사 본문 및 비정형 원본 데이터 (PostgreSQL JSONB).

    user_saved_article_id 는 MySQL 역할의 user_saved_article.id 를 참조한다.
    RDB 간 경계를 넘는 외래키는 걸지 않고 애플리케이션 레이어에서 일관성을 관리한다.
    """

    __tablename__ = "interest_article_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_saved_article_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
