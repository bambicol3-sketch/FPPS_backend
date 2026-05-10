from dataclasses import dataclass
from typing import Optional


@dataclass
class GoogleUserInfo:
    google_id: str
    nickname: Optional[str]
    email: Optional[str]
