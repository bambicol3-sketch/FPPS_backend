from abc import ABC, abstractmethod
from typing import List


class FabLlmPort(ABC):
    """OpenAI 호환 chat.completions 기반 LLM 포트.

    base_url 교체만으로 온프레미스(vLLM/TGI) 서빙과 호환된다.
    """

    @abstractmethod
    async def answer(self, system_instructions: str, user_prompt: str) -> str:
        raise NotImplementedError


class FabEmbeddingPort(ABC):
    """OpenAI 호환 임베딩 포트 (온프레미스 TEI 등으로 교체 가능)."""

    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        raise NotImplementedError

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError
