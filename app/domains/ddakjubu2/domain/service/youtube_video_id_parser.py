import re
from typing import Optional

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")

URL_PATTERNS = [
    re.compile(r"[?&]v=([A-Za-z0-9_-]{11})"),           # watch?v=ID
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),        # youtu.be/ID
    re.compile(r"/live/([A-Za-z0-9_-]{11})"),            # /live/ID
    re.compile(r"/shorts/([A-Za-z0-9_-]{11})"),          # /shorts/ID
    re.compile(r"/embed/([A-Za-z0-9_-]{11})"),           # /embed/ID
]


def extract_video_id(text: str) -> Optional[str]:
    """YouTube URL 또는 11자 video_id 문자열에서 video_id 를 추출한다."""
    candidate = (text or "").strip()
    if not candidate:
        return None
    if VIDEO_ID_PATTERN.match(candidate):
        return candidate
    for pattern in URL_PATTERNS:
        match = pattern.search(candidate)
        if match:
            return match.group(1)
    return None
