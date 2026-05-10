from dataclasses import dataclass
from typing import Optional


@dataclass
class GoogleToken:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None
