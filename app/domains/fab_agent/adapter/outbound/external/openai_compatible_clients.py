from typing import List, Optional

from openai import AsyncOpenAI

from app.domains.fab_agent.application.port.fab_llm_ports import (
    FabEmbeddingPort,
    FabLlmPort,
)

EMBED_BATCH_SIZE = 64


def _build_client(api_key: str, base_url: str) -> AsyncOpenAI:
    """base_url 이 비어 있으면 OpenAI, 지정되면 온프레미스 OpenAI 호환 서버(vLLM/TGI/TEI)."""
    kwargs = {"api_key": api_key or "on-prem"}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncOpenAI(**kwargs)


class OpenAICompatibleLlmClient(FabLlmPort):
    """chat.completions 기반 — vLLM 등 OpenAI 호환 온프레미스 서빙과 그대로 호환."""

    def __init__(self, api_key: str, model: str, base_url: str = ""):
        self._client = _build_client(api_key, base_url)
        self._model = model

    async def answer(self, system_instructions: str, user_prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_instructions},
                {"role": "user", "content": user_prompt},
            ],
        )
        if not response.choices:
            return ""
        return response.choices[0].message.content or ""


class OpenAICompatibleEmbeddingClient(FabEmbeddingPort):
    def __init__(self, api_key: str, model: str, base_url: str = ""):
        self._client = _build_client(api_key, base_url)
        self._model = model

    async def embed(self, text: str) -> List[float]:
        response = await self._client.embeddings.create(
            model=self._model, input=text
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        if not texts:
            return []
        embeddings: List[Optional[List[float]]] = []
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i:i + EMBED_BATCH_SIZE]
            response = await self._client.embeddings.create(
                model=self._model, input=batch
            )
            ordered = sorted(response.data, key=lambda d: d.index)
            embeddings.extend([d.embedding for d in ordered])
        return embeddings
