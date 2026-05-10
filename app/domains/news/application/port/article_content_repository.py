from abc import ABC, abstractmethod


class ArticleContentRepository(ABC):

    @abstractmethod
    async def save(self, user_saved_article_id: int, content: str | None, snippet: str | None) -> None:
        pass

    async def save_payload(self, user_saved_article_id: int, payload: dict) -> None:
        """원본 JSONB payload 전체를 저장한다. 기본 구현은 save를 호출한다."""
        scraped = payload.get("scraped_content") if isinstance(payload, dict) else None
        snippet = payload.get("snippet") if isinstance(payload, dict) else None
        await self.save(
            user_saved_article_id=user_saved_article_id,
            content=scraped,
            snippet=snippet,
        )
