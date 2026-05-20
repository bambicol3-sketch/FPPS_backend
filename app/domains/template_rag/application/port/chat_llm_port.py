from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.domains.template_rag.domain.entity.chat_session import ChatMessage


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class ChatLlmResponse:
    content: Optional[str]
    tool_call: Optional[ToolCall] = None


class ChatLlmPort(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        system: str,
    ) -> ChatLlmResponse: ...
