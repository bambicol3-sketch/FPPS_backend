from abc import ABC, abstractmethod
from typing import Any


class LlmJsonClientPort(ABC):
    @abstractmethod
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        """system + user 프롬프트를 받아 JSON 객체로 응답."""
