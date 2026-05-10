import logging
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.infrastructure.config.settings import get_settings
from app.infrastructure.multi_agent.exceptions import LLMInvocationError

logger = logging.getLogger(__name__)


@lru_cache
def get_multi_agent_llm() -> BaseChatModel:
    """환경변수 기반 LLM 클라이언트 싱글톤."""
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMInvocationError(
            node="bootstrap",
            reason="OPENAI_API_KEY 가 설정되지 않았습니다.",
        )
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.multi_agent_model,
        temperature=settings.multi_agent_temperature,
        max_tokens=settings.multi_agent_max_tokens,
        timeout=settings.multi_agent_request_timeout,
    )


async def invoke_llm(node: str, system_prompt: str, user_prompt: str) -> str:
    """단일 LLM 호출 래퍼.

    실패 시 `LLMInvocationError` 로 정규화하여 전파한다.
    """
    llm = get_multi_agent_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    try:
        response = await llm.ainvoke(messages)
    except LLMInvocationError:
        raise
    except Exception as exc:
        logger.exception("[multi_agent.%s] LLM 호출 실패", node)
        raise LLMInvocationError(node=node, reason=str(exc)) from exc

    content = getattr(response, "content", "")
    if isinstance(content, list):
        # 다중 블록 응답을 단일 문자열로 병합
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return (content or "").strip()
