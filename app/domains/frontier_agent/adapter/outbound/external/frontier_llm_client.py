from openai import AsyncOpenAI

from app.domains.frontier_agent.application.port.frontier_ports import FrontierLlmPort


class OpenAICompatibleFrontierLlm(FrontierLlmPort):
    """chat.completions 기반 — base_url 지정 시 온프레미스(vLLM/TGI) 서빙과 호환."""

    def __init__(self, api_key: str, model: str, base_url: str = ""):
        kwargs = {"api_key": api_key or "on-prem"}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = model

    async def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        if not response.choices:
            return ""
        return response.choices[0].message.content or ""
