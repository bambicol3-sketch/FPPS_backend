from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from app.domains.fab_agent.domain.entity.fab_user_access import FabUserAccess


class FabAccessRepositoryPort(ABC):
    @abstractmethod
    async def get_access(self, account_email: str) -> Optional[FabUserAccess]:
        raise NotImplementedError

    @abstractmethod
    async def upsert_access(self, access: FabUserAccess) -> None:
        raise NotImplementedError

    @abstractmethod
    async def list_access(self) -> List[FabUserAccess]:
        raise NotImplementedError


class FabAuditRepositoryPort(ABC):
    """불변 감사 로그 포트 — 저장과 조회만 존재한다 (수정·삭제 없음)."""

    @abstractmethod
    async def save(
        self,
        request_id: str,
        account_email: str,
        session_id: str,
        question: str,
        answer: str,
        citations: List[dict],
        used_grade_max: int,
        refused: bool,
        latency_ms: int,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def find_recent(
        self, limit: int, account_email: Optional[str] = None
    ) -> List[dict]:
        raise NotImplementedError


class FabChatRepositoryPort(ABC):
    @abstractmethod
    async def recent_messages(
        self, session_id: str, limit: int
    ) -> List[Tuple[str, str]]:
        """(role, content) 목록, 오래된 것부터."""
        raise NotImplementedError

    @abstractmethod
    async def save_message(
        self,
        session_id: str,
        account_email: str,
        role: str,
        content: str,
        citations: Optional[List[dict]] = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def session_messages(
        self, session_id: str, account_email: str
    ) -> List[dict]:
        raise NotImplementedError


class FabFeedbackRepositoryPort(ABC):
    @abstractmethod
    async def save(
        self,
        request_id: str,
        account_email: str,
        rating: str,
        reason: Optional[str],
    ) -> None:
        raise NotImplementedError
