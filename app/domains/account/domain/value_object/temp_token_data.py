from dataclasses import dataclass
from typing import Optional


@dataclass
class TempTokenData:
    oauth_access_token: str
    nickname: Optional[str]
    email: Optional[str]
    provider: str = "kakao"
