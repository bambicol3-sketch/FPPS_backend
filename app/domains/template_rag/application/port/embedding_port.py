from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    @abstractmethod
    async def generate(self, text: str) -> list[float]: ...

    @abstractmethod
    async def generate_batch(self, texts: list[str]) -> list[list[float]]: ...
