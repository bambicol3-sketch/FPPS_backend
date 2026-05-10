import asyncio
import logging
from typing import List

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from app.domains.macro.application.port.macro_transcript_fetch_port import (
    MacroTranscriptFetchPort,
)

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGES: List[str] = ["ko", "ko-KR", "en", "en-US"]


class YoutubeTranscriptClient(MacroTranscriptFetchPort):
    """youtube-transcript-api 기반 자막 추출 어댑터."""

    def __init__(self):
        self._api = YouTubeTranscriptApi()

    async def fetch_transcript(self, video_id: str) -> str:
        try:
            fetched = await asyncio.to_thread(
                self._api.fetch,
                video_id,
                DEFAULT_LANGUAGES,
            )
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
            logger.info(
                "[macro_transcript] 자막 없음 video_id=%s reason=%s",
                video_id,
                type(e).__name__,
            )
            return ""
        except Exception as e:
            logger.warning(
                "[macro_transcript] 자막 추출 실패 video_id=%s error=%s",
                video_id,
                e,
            )
            return ""

        return " ".join(
            snippet.text.strip()
            for snippet in fetched
            if getattr(snippet, "text", "")
        ).strip()
