from typing import Optional

from pydantic import BaseModel


class GoogleUserInfoResponse(BaseModel):
    google_id: str
    nickname: Optional[str]
    email: Optional[str]
