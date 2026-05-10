import logging
from functools import lru_cache
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.infrastructure.config.settings import get_settings
from app.infrastructure.multi_agent.nodes import (
    analyst_node,
    planner_node,
    researcher_node,
    reviewer_node,
)
from app.infrastructure.multi_agent.state import AgentState

logger = logging.getLogger(__name__)


def _route_after_reviewer(state: AgentState) -> Literal["analyst", "__end__"]:
    """Reviewer 결과에 따라 재분석 또는 종료를 결정한다."""
    max_steps = get_settings().multi_agent_max_steps
    if state.get("step_count", 0) >= max_steps:
        logger.info(
            "[multi_agent.route] max_steps(%s) 도달 → END",
            max_steps,
        )
        return "__end__"

    review = (state.get("review") or "").strip()
    first_line = review.partition("\n")[0].strip().upper()
    if first_line.startswith("REVISE"):
        logger.info("[multi_agent.route] Reviewer REVISE 요청 → analyst 재실행")
        return "analyst"
    return "__end__"


def build_multi_agent_graph():
    """Planner → Researcher → Analyst → Reviewer 파이프라인 그래프."""
    builder = StateGraph(AgentState)

    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("reviewer", reviewer_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "analyst")
    builder.add_edge("analyst", "reviewer")
    builder.add_conditional_edges(
        "reviewer",
        _route_after_reviewer,
        {
            "analyst": "analyst",
            "__end__": END,
        },
    )

    return builder.compile()


@lru_cache
def get_multi_agent_graph():
    """컴파일된 그래프 싱글톤."""
    return build_multi_agent_graph()
