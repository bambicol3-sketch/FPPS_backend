from typing import Optional

from pydantic import BaseModel


class ChatMessageDTO(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    status: str  # "active" | "done"
    result: Optional[dict] = None


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageDTO]
    status: str
    result: Optional[dict] = None
