import logging

from openai import AsyncOpenAI

from app.domains.template_rag.application.port.embedding_port import EmbeddingPort
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


class OpenAIEmbeddingClient(EmbeddingPort):
    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=EMBEDDING_MODEL, input=text
        )
        return response.data[0].embedding

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            response = await self._client.embeddings.create(
                model=EMBEDDING_MODEL, input=batch
            )
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend(item.embedding for item in sorted_data)
        logger.info("[TemplateRAG] embedded %d texts", len(texts))
        return all_embeddings
