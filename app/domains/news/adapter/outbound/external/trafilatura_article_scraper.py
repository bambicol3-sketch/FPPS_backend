import asyncio
import logging
from typing import Any

import httpx
import trafilatura

from app.domains.news.application.port.article_content_provider import (
    ArticleContentProvider,
)

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class TrafilaturaArticleScraper(ArticleContentProvider):
    """trafilatura 기반 기사 본문 추출 Adapter.

    대부분의 뉴스 사이트에서 본문/광고/네비게이션을 분리한다.
    """

    def __init__(self, timeout_seconds: float = 15.0):
        self._timeout = timeout_seconds

    async def fetch_content(self, url: str) -> str:
        data = await self.fetch_article(url)
        return data.get("scraped_content") or ""

    async def fetch_article(self, url: str) -> dict:
        html = await self._download(url)
        if not html:
            return {
                "scraped_content": None,
                "extractor": "trafilatura",
                "success": False,
                "reason": "download_failed",
            }

        try:
            extraction: dict[str, Any] | None = await asyncio.to_thread(
                self._extract_sync, html, url
            )
        except Exception as e:
            logger.warning("[TrafilaturaArticleScraper] extraction failed url=%s err=%s", url, e)
            return {
                "scraped_content": None,
                "extractor": "trafilatura",
                "success": False,
                "reason": f"extraction_error: {e}",
                "raw_html_length": len(html),
            }

        if not extraction or not extraction.get("text"):
            return {
                "scraped_content": None,
                "extractor": "trafilatura",
                "success": False,
                "reason": "empty_text",
                "raw_html_length": len(html),
            }

        text = extraction.get("text") or ""
        return {
            "scraped_content": text,
            "extractor": "trafilatura",
            "success": True,
            "content_length": len(text),
            "raw_html_length": len(html),
            "metadata": {
                "title": extraction.get("title"),
                "author": extraction.get("author"),
                "date": extraction.get("date"),
                "sitename": extraction.get("sitename"),
                "categories": extraction.get("categories"),
                "tags": extraction.get("tags"),
                "description": extraction.get("description"),
                "language": extraction.get("language"),
                "url": extraction.get("url") or url,
            },
        }

    async def _download(self, url: str) -> str | None:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning("[TrafilaturaArticleScraper] download failed url=%s err=%s", url, e)
            return None

    @staticmethod
    def _extract_sync(html: str, url: str) -> dict[str, Any] | None:
        result = trafilatura.extract(
            html,
            url=url,
            output_format="json",
            include_comments=False,
            include_tables=False,
            with_metadata=True,
            favor_precision=True,
        )
        if not result:
            return None
        import json

        return json.loads(result)
