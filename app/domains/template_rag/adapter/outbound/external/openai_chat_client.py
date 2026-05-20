import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.domains.template_rag.application.port.chat_llm_port import (
    ChatLlmPort,
    ChatLlmResponse,
    ToolCall,
)
from app.domains.template_rag.domain.entity.chat_session import ChatMessage
from app.domains.template_rag.domain.value_object.form_type import FormType
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

_GENERATE_PPTX_TOOL = {
    "type": "function",
    "function": {
        "name": "generate_pptx",
        "description": "PPT를 생성합니다. form_type과 raw_data_dir가 모두 확인된 후 호출하세요.",
        "parameters": {
            "type": "object",
            "properties": {
                "form_type": {
                    "type": "string",
                    "enum": [ft.value for ft in FormType],
                    "description": "양식 종류",
                },
                "raw_data_dir": {
                    "type": "string",
                    "description": "raw data 파일들이 있는 폴더의 절대 경로",
                },
            },
            "required": ["form_type", "raw_data_dir"],
        },
    },
}


class OpenAIChatClient(ChatLlmPort):
    """OpenAI Chat Completions + function calling 기반 대화형 클라이언트."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_finance_agent_model

    async def chat(
        self,
        messages: list[ChatMessage],
        system: str,
    ) -> ChatLlmResponse:
        openai_messages = [{"role": "system", "content": system}]
        openai_messages += [{"role": m.role, "content": m.content} for m in messages]

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                tools=[_GENERATE_PPTX_TOOL],
                tool_choice="auto",
            )
        except Exception as e:
            logger.error("[OpenAIChatClient] API 호출 실패: %s", e)
            return ChatLlmResponse(content=f"LLM 호출 중 오류가 발생했습니다: {e}")

        choice = response.choices[0]
        msg = choice.message

        if msg.tool_calls:
            tc = msg.tool_calls[0]
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            return ChatLlmResponse(
                content=None,
                tool_call=ToolCall(name=tc.function.name, arguments=args),
            )

        return ChatLlmResponse(content=msg.content or "")
