from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news.application.port.article_content_repository import ArticleContentRepository
from app.domains.news.infrastructure.orm.interest_article_content_orm import (
    InterestArticleContentOrm,
)


class ArticleContentRepositoryImpl(ArticleContentRepository):
    """관심 기사 본문 저장소 (PostgreSQL JSONB — interest_article_contents 테이블)."""

    def __init__(self, vector_db: AsyncSession):
        self._db = vector_db

    async def save(self, user_saved_article_id: int, content: str | None, snippet: str | None) -> None:
        payload: dict = {}
        if content:
            payload["scraped_content"] = content
        if snippet:
            payload["snippet"] = snippet

        await self._persist(user_saved_article_id, payload or None)

    async def save_payload(self, user_saved_article_id: int, payload: dict) -> None:
        await self._persist(user_saved_article_id, payload or None)

    async def _persist(self, user_saved_article_id: int, content: dict | None) -> None:
        orm = InterestArticleContentOrm(
            user_saved_article_id=user_saved_article_id,
            content=content,
        )
        self._db.add(orm)
        await self._db.commit()
