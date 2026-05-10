import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.domains.macro.application.port.macro_video_fetch_port import MacroVideoFetchPort
from app.domains.macro.domain.entity.reference_video import ReferenceVideo

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class YoutubeRecentVideoClient(MacroVideoFetchPort):
    """YouTube Data API v3으로 지정 채널의 최근 업로드 영상을 조회한다."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def fetch_recent_videos(
        self,
        channel_ids: List[str],
        published_after: datetime,
        max_per_channel: int = 20,
    ) -> List[ReferenceVideo]:
        if not channel_ids:
            return []

        published_after_str = published_after.astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        results: List[ReferenceVideo] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for channel_id in channel_ids:
                search_items = await self._search_channel(
                    client, channel_id, published_after_str, max_per_channel
                )
                if not search_items:
                    continue

                video_ids = [
                    item.get("id", {}).get("videoId")
                    for item in search_items
                    if item.get("id", {}).get("videoId")
                ]
                if not video_ids:
                    continue

                details = await self._fetch_details(client, video_ids)

                for item in search_items:
                    video_id = item.get("id", {}).get("videoId")
                    if not video_id:
                        continue

                    detail_snippet = (
                        details.get(video_id, {}).get("snippet")
                        or item.get("snippet")
                        or {}
                    )
                    description = detail_snippet.get("description", "")
                    title = detail_snippet.get("title", "")
                    channel_name = detail_snippet.get("channelTitle", "")
                    published_at = self._parse_datetime(detail_snippet.get("publishedAt"))

                    results.append(
                        ReferenceVideo(
                            video_id=video_id,
                            title=title,
                            description=description,
                            transcript="",
                            channel_id=channel_id,
                            channel_name=channel_name,
                            published_at=published_at,
                            video_url=f"https://www.youtube.com/watch?v={video_id}",
                        )
                    )

        return results

    async def _search_channel(
        self,
        client: httpx.AsyncClient,
        channel_id: str,
        published_after: str,
        max_results: int,
    ) -> List[dict]:
        try:
            response = await client.get(
                YOUTUBE_SEARCH_URL,
                params={
                    "key": self._api_key,
                    "channelId": channel_id,
                    "part": "snippet",
                    "type": "video",
                    "order": "date",
                    "publishedAfter": published_after,
                    "maxResults": max_results,
                },
            )
            if response.status_code != 200:
                logger.warning(
                    "[macro_youtube] search status=%s body=%s",
                    response.status_code,
                    response.text[:200],
                )
                return []
            return response.json().get("items", [])
        except Exception as e:
            logger.warning("[macro_youtube] search 예외 channel=%s error=%s", channel_id, e)
            return []

    async def _fetch_details(
        self,
        client: httpx.AsyncClient,
        video_ids: List[str],
    ) -> dict:
        result: dict = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            try:
                response = await client.get(
                    YOUTUBE_VIDEOS_URL,
                    params={
                        "key": self._api_key,
                        "id": ",".join(batch),
                        "part": "snippet",
                    },
                )
                if response.status_code != 200:
                    continue
                for item in response.json().get("items", []):
                    vid = item.get("id")
                    if vid:
                        result[vid] = item
            except Exception as e:
                logger.warning("[macro_youtube] videos.list 예외 error=%s", e)
                continue
        return result

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)
