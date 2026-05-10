import logging
from typing import Callable

from app.infrastructure.multi_agent.exceptions import GraphExecutionError, LLMInvocationError
from app.infrastructure.multi_agent.llm_client import invoke_llm
from app.infrastructure.multi_agent.state import AgentMessage, AgentState

logger = logging.getLogger(__name__)


PLANNER_SYSTEM = """당신은 멀티 에이전트 오케스트레이터의 Planner 입니다.
사용자 질문을 3단계 이내의 한국어 실행 계획으로 분해하세요.
각 단계는 한 줄로 간결하게, 숫자 접두어(1., 2., 3.)를 사용하세요."""

RESEARCHER_SYSTEM = """당신은 Researcher 입니다.
주어진 계획을 바탕으로 답변에 필요한 핵심 사실/배경/참고 포인트를 한국어로 정리하세요.
외부 검색은 사용하지 않으며, 모델이 알고 있는 상식 기반으로 요약합니다."""

ANALYST_SYSTEM = """당신은 Analyst 입니다.
Researcher 가 수집한 자료를 바탕으로 사용자 질문에 대한 구체적이고 실행 가능한 분석을
한국어로 3~5문장으로 작성하세요."""

REVIEWER_SYSTEM = """당신은 Reviewer 입니다.
이전 노드의 분석 결과가 사용자 질문에 충분히 답했는지 검토하고,
부족하면 'REVISE: <사유>' 로 시작하는 한 줄, 충분하면 'OK' 로 시작하는 한 줄을 작성한 뒤
사용자에게 전달할 최종 답변(한국어)을 아래에 3문장 이내로 작성하세요."""


def _append_message(node: str, role: str, content: str) -> AgentMessage:
    return AgentMessage(role=role, node=node, content=content)  # type: ignore[arg-type]


def _log_node_entry(node: str, state: AgentState) -> None:
    logger.info(
        "[multi_agent.%s] enter step=%s query=%r",
        node,
        state.get("step_count", 0),
        (state.get("query") or "")[:80],
    )


def _log_node_exit(node: str, output_len: int) -> None:
    logger.info("[multi_agent.%s] exit output_chars=%s", node, output_len)


async def planner_node(state: AgentState) -> dict:
    node = "planner"
    _log_node_entry(node, state)
    try:
        plan = await invoke_llm(
            node=node,
            system_prompt=PLANNER_SYSTEM,
            user_prompt=f"사용자 질문:\n{state['query']}",
        )
    except LLMInvocationError:
        raise
    except Exception as exc:
        raise GraphExecutionError(node=node, reason=str(exc)) from exc

    _log_node_exit(node, len(plan))
    return {
        "plan": plan,
        "step_count": state.get("step_count", 0) + 1,
        "messages": [_append_message(node, "planner", plan)],
    }


async def researcher_node(state: AgentState) -> dict:
    node = "researcher"
    _log_node_entry(node, state)
    prompt = (
        f"질문: {state['query']}\n\n"
        f"Planner 가 제시한 계획:\n{state.get('plan', '(없음)')}\n\n"
        "위 계획을 참고하여 답변에 필요한 자료를 정리해 주세요."
    )
    try:
        research = await invoke_llm(
            node=node, system_prompt=RESEARCHER_SYSTEM, user_prompt=prompt
        )
    except LLMInvocationError:
        raise
    except Exception as exc:
        raise GraphExecutionError(node=node, reason=str(exc)) from exc

    _log_node_exit(node, len(research))
    return {
        "research": research,
        "step_count": state.get("step_count", 0) + 1,
        "messages": [_append_message(node, "researcher", research)],
    }


async def analyst_node(state: AgentState) -> dict:
    node = "analyst"
    _log_node_entry(node, state)
    prompt = (
        f"질문: {state['query']}\n\n"
        f"자료:\n{state.get('research', '(없음)')}\n\n"
        "위 자료를 기반으로 분석을 작성해 주세요."
    )
    try:
        analysis = await invoke_llm(
            node=node, system_prompt=ANALYST_SYSTEM, user_prompt=prompt
        )
    except LLMInvocationError:
        raise
    except Exception as exc:
        raise GraphExecutionError(node=node, reason=str(exc)) from exc

    _log_node_exit(node, len(analysis))
    return {
        "analysis": analysis,
        "step_count": state.get("step_count", 0) + 1,
        "messages": [_append_message(node, "analyst", analysis)],
    }


async def reviewer_node(state: AgentState) -> dict:
    node = "reviewer"
    _log_node_entry(node, state)
    prompt = (
        f"사용자 질문: {state['query']}\n\n"
        f"Analyst 의 분석:\n{state.get('analysis', '(없음)')}\n\n"
        "위 분석을 검토하고 최종 답변을 작성해 주세요."
    )
    try:
        review = await invoke_llm(
            node=node, system_prompt=REVIEWER_SYSTEM, user_prompt=prompt
        )
    except LLMInvocationError:
        raise
    except Exception as exc:
        raise GraphExecutionError(node=node, reason=str(exc)) from exc

    # 'REVISE: ...' 로 시작하면 재작업, 'OK' 면 최종 답변 확정
    first_line, _, rest = review.partition("\n")
    needs_revision = first_line.strip().upper().startswith("REVISE")
    if needs_revision:
        final_answer = ""
    else:
        stripped_head = first_line.lstrip()
        if stripped_head.upper().startswith("OK"):
            head_rest = stripped_head[2:].lstrip(":,.;-–— \t")
        else:
            head_rest = first_line
        final_answer = (head_rest + ("\n" + rest if rest else "")).strip() or state.get(
            "analysis", ""
        )

    _log_node_exit(node, len(review))
    return {
        "review": review,
        "final_answer": final_answer or state.get("final_answer", ""),
        "step_count": state.get("step_count", 0) + 1,
        "messages": [_append_message(node, "reviewer", review)],
    }


NodeFn = Callable[[AgentState], dict]

NODES: dict[str, NodeFn] = {
    "planner": planner_node,
    "researcher": researcher_node,
    "analyst": analyst_node,
    "reviewer": reviewer_node,
}
