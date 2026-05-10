from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.domains.investment.adapter.outbound.workflow.nodes import (
    analysis_node,
    orchestrator_node,
    retrieval_node,
    synthesis_node,
)
from app.domains.investment.adapter.outbound.workflow.state import (
    InvestmentAgentState,
    NextAgent,
)

MAX_ITERATIONS = 8


def _route_from_orchestrator(state: InvestmentAgentState) -> NextAgent:
    """Orchestrator 가 결정한 next_agent 로 라우팅 (반복 제한 적용)."""
    iteration = state.get("iteration", 0)
    if iteration >= MAX_ITERATIONS:
        print(
            f"[investment.route] max_iterations({MAX_ITERATIONS}) reached → end",
            flush=True,
        )
        return "end"

    decision: NextAgent = state.get("next_agent") or "end"
    print(f"[investment.route] routing -> {decision}", flush=True)
    return decision


def build_investment_graph():
    """Orchestrator 중심의 투자 판단 워크플로우 그래프.

        ┌──────────────┐
        │ orchestrator │◀──────────────────┐
        └──────┬───────┘                   │
               ▼                           │
     ┌─────────┬─────────┬──────────┐      │
     │retrieval│ analysis│ synthesis│──►end│
     └────┬────┴────┬────┴─────┬────┘      │
          │         │          │            │
          └────┬────┴──────────┘            │
               │                            │
               └────────────────────────────┘
    """
    builder = StateGraph(InvestmentAgentState)

    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("synthesis", synthesis_node)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        _route_from_orchestrator,
        {
            "retrieval": "retrieval",
            "analysis": "analysis",
            "synthesis": "synthesis",
            "end": END,
        },
    )

    # 각 Agent 실행 후 다시 Orchestrator 로 돌아와 다음 단계를 결정
    builder.add_edge("retrieval", "orchestrator")
    builder.add_edge("analysis", "orchestrator")
    builder.add_edge("synthesis", "orchestrator")

    return builder.compile()


@lru_cache
def get_investment_graph():
    """컴파일된 그래프 싱글톤."""
    return build_investment_graph()
