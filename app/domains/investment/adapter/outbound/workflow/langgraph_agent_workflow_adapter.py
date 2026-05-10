from app.domains.investment.adapter.outbound.workflow.runner import (
    AgentWorkflowInput,
    run_agent_workflow,
)
from app.domains.investment.application.port.out.agent_workflow_port import (
    AgentWorkflowPort,
)
from app.domains.investment.application.response.investment_decision_response import (
    InvestmentDecisionResponse,
)


class LangGraphAgentWorkflowAdapter(AgentWorkflowPort):
    """`run_agent_workflow` LangGraph 실행 결과를 Application 응답 DTO 로 변환."""

    async def run(self, account_id: int, query: str) -> InvestmentDecisionResponse:
        result = await run_agent_workflow(
            AgentWorkflowInput(query=query, account_id=account_id)
        )
        return InvestmentDecisionResponse(
            query=result.query,
            answer=result.answer,
            iterations=result.iterations,
            trace=result.trace,
        )
