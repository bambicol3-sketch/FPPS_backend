from abc import ABC, abstractmethod
from typing import Optional

from app.domains.template_rag.domain.entity.chat_session import ChatSession


class ChatSessionStorePort(ABC):
    @abstractmethod
    def save(self, session: ChatSession) -> None: ...

    @abstractmethod
    def load(self, session_id: str) -> Optional[ChatSession]: ...
