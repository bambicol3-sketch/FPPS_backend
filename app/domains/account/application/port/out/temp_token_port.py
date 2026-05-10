from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class TempTokenInfo:
    nickname: Optional[str] = None
    email: Optional[str] = None
    kakao_access_token: Optional[str] = None


class TempTokenPort(ABC):
    @abstractmethod
    async def find_by_token(self, token: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def delete_by_token(self, token: str) -> None:
        pass
