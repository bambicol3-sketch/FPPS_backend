from abc import ABC, abstractmethod


class ArticleContentProvider(ABC):

    @abstractmethod
    async def fetch_content(self, url: str) -> str:
        """기사 링크에 접근하여 본문 내용을 추출한다."""
        pass

    async def fetch_article(self, url: str) -> dict:
        """본문 + 비정형 메타데이터(원본 HTML 메타, 추출 성공 여부 등)를 반환한다.

        기본 구현은 fetch_content만을 사용한다. 구체 구현체가 재정의할 수 있다.
        """
        content = await self.fetch_content(url)
        return {
            "scraped_content": content or None,
            "extractor": "default",
            "success": bool(content),
        }
