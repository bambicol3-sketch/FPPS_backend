from abc import ABC, abstractmethod

from app.domains.google_auth.domain.entity.google_token import GoogleToken


class GoogleTokenPort(ABC):
    @abstractmethod
    async def fetch_token(self, code: str) -> GoogleToken:
        pass
