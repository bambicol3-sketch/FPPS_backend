import logging
from dataclasses import dataclass, field
from typing import Any

from app.infrastructure.multi_agent.exceptions import (
    GraphExecutionError,
    LLMInvocationError,
    MultiAgentError,
)
from app.infrastructure.multi_agent.graph import get_multi_agent_graph
from app.infrastructure.multi_agent.state import AgentMessage, AgentState

logger = logging.getLogger(__name__)


@dataclass
class MultiAgentInput:
    query: str
    memory: dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiAgentOutput:
    final_answer: str
    plan: str
    research: str
    analysis: str
    review: str
    messages: list[AgentMessage]
    step_count: int


async def run_multi_agent(input_: MultiAgentInput) -> MultiAgentOutput:
    """그래프 단일 진입점.

    입력 → 중간 상태 → 최종 출력 흐름을 일관된 인터페이스로 제공한다.
    실패 시 MultiAgentError 계열 예외가 전파된다.
    """
    if not input_.query or not input_.query.strip():
        raise MultiAgentError("query 가 비어 있습니다.")

    graph = get_multi_agent_graph()
    initial_state: AgentState = {
        "query": input_.query.strip(),
        "messages": [],
        "memory": input_.memory or {},
        "step_count": 0,
    }

    logger.info("[multi_agent.runner] start query=%r", initial_state["query"][:80])
    try:
        final_state: AgentState = await graph.ainvoke(initial_state)
    except (LLMInvocationError, GraphExecutionError):
        raise
    except Exception as exc:
        logger.exception("[multi_agent.runner] 그래프 실행 중 예외")
        raise GraphExecutionError(node="graph", reason=str(exc)) from exc

    final_answer = (final_state.get("final_answer") or "").strip()
    if not final_answer:
        # Reviewer 가 REVISE 만 반복하며 루프를 끝냈을 때 → Analyst 결과로 폴백
        final_answer = (final_state.get("analysis") or "").strip()

    logger.info(
        "[multi_agent.runner] done steps=%s answer_chars=%s",
        final_state.get("step_count", 0),
        len(final_answer),
    )

    return MultiAgentOutput(
        final_answer=final_answer,
        plan=final_state.get("plan", ""),
        research=final_state.get("research", ""),
        analysis=final_state.get("analysis", ""),
        review=final_state.get("review", ""),
        messages=list(final_state.get("messages", [])),
        step_count=int(final_state.get("step_count", 0)),
    )
