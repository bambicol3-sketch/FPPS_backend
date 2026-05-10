from abc import ABC, abstractmethod

from app.domains.google_auth.domain.entity.google_user_info import GoogleUserInfo


class GoogleUserInfoPort(ABC):
    @abstractmethod
    async def fetch_user_info(self, access_token: str) -> GoogleUserInfo:
        pass
