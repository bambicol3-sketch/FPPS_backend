from typing import Optional

from app.domains.template_rag.application.port.chat_session_store_port import (
    ChatSessionStorePort,
)
from app.domains.template_rag.domain.entity.chat_session import ChatSession


class InMemoryChatSessionStore(ChatSessionStorePort):
    """프로세스 내 메모리 기반 세션 저장소. 서버 재시작 시 휘발됨."""

    def __init__(self) -> None:
        self._store: dict[str, ChatSession] = {}

    def save(self, session: ChatSession) -> None:
        self._store[session.session_id] = session

    def load(self, session_id: str) -> Optional[ChatSession]:
        return self._store.get(session_id)
