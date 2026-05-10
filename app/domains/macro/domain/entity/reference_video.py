from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ReferenceVideo:
    video_id: str
    title: str
    description: str
    transcript: str
    channel_id: str
    channel_name: str
    published_at: datetime
    video_url: str = ""

    def short_context(self, max_transcript_chars: int = 2000) -> str:
        transcript_block = (
            self.transcript[:max_transcript_chars].strip()
            if self.transcript
            else "(자막 없음)"
        )
        return (
            f"[video_id] {self.video_id}\n"
            f"[제목] {self.title}\n"
            f"[업로드] {self.published_at.strftime('%Y-%m-%d')}\n"
            f"[설명] {self.description.strip()[:500]}\n"
            f"[자막 발췌]\n{transcript_block}"
        )
