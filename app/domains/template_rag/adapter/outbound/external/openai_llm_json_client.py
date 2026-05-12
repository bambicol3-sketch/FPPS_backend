import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.domains.template_rag.application.port.llm_json_client_port import (
    LlmJsonClientPort,
)
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class OpenAILlmJsonClient(LlmJsonClientPort):
    """OpenAI Responses API + JSON 출력 모드 클라이언트.

    프롬프트 안에서도 'JSON 으로만 응답' 을 명시하고, text.format=json_object 로 강제.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_finance_agent_model  # 기본 gpt-5-mini

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict[str, Any]:
        prompt = (
            f"[지시사항]\n{system_prompt}\n\n"
            f"[입력]\n{user_prompt}\n\n"
            f"[출력 형식] 위 지시사항에서 명시한 JSON 객체 하나만 반환. "
            f"마크다운/설명 없이 JSON 그 자체만."
        )
        try:
            response = await self._client.responses.create(
                model=self._model,
                input=prompt,
                text={"format": {"type": "json_object"}},
            )
        except TypeError:
            # 일부 SDK 버전 호환: text 인자 미지원이면 그냥 입력만 전달
            response = await self._client.responses.create(
                model=self._model,
                input=prompt,
            )

        text = response.output_text or ""
        text = text.strip()
        # 혹시 ```json 펜스가 붙어도 제거
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(
                "[OpenAILlmJsonClient] JSON 파싱 실패: %s | raw=%s", e, text[:500]
            )
            # 최후 폴백 — 빈 dict 반환
            return {}
