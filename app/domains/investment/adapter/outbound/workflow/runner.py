from dataclasses import dataclass, field

from app.domains.investment.adapter.outbound.workflow.graph import get_investment_graph
from app.domains.investment.adapter.outbound.workflow.state import InvestmentAgentState


@dataclass
class AgentWorkflowInput:
    query: str
    account_id: int | None = None


@dataclass
class AgentWorkflowOutput:
    query: str
    answer: str
    iterations: int
    trace: list[str] = field(default_factory=list)


async def run_agent_workflow(input_: AgentWorkflowInput) -> AgentWorkflowOutput:
    """투자 판단 멀티 에이전트 워크플로우 단일 진입점.

    흐름:
        1. 초기 State 구성
        2. LangGraph 실행 (ainvoke)
        3. 최종 State → AgentWorkflowOutput 변환
        4. LLM/외부 호출 실패 시 상위로 예외 전파
    """
    if not input_.query or not input_.query.strip():
        raise ValueError("query 가 비어 있습니다.")

    graph = get_investment_graph()
    initial_state: InvestmentAgentState = {
        "query": input_.query.strip(),
        "account_id": input_.account_id or 0,
        "iteration": 0,
        "trace": [],
    }

    print(f"[investment.runner] start query={initial_state['query'][:60]!r}", flush=True)

    final_state: InvestmentAgentState = await graph.ainvoke(initial_state)

    answer = (final_state.get("synthesis_answer") or "").strip()
    iterations = int(final_state.get("iteration", 0))
    trace = list(final_state.get("trace") or [])

    print(
        f"[investment.runner] done iterations={iterations} answer_chars={len(answer)}",
        flush=True,
    )

    return AgentWorkflowOutput(
        query=initial_state["query"],
        answer=answer or "(응답 생성 실패)",
        iterations=iterations,
        trace=trace,
    )
