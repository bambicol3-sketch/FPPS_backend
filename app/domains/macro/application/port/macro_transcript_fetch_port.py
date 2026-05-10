from abc import ABC, abstractmethod


class MacroTranscriptFetchPort(ABC):
    """영상 자막/스크립트 추출 포트."""

    @abstractmethod
    async def fetch_transcript(self, video_id: str) -> str:
        """자막 없거나 실패 시 빈 문자열을 반환한다."""
        raise NotImplementedError
