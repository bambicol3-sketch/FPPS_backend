from app.domains.investment.application.port.out.agent_workflow_port import (
    AgentWorkflowPort,
)
from app.domains.investment.application.request.investment_decision_request import (
    InvestmentDecisionRequest,
)
from app.domains.investment.application.response.investment_decision_response import (
    InvestmentDecisionResponse,
)


class MakeInvestmentDecisionUseCase:
    """투자 판단 요청 UseCase.

    Router 가 인증을 통과한 account_id 와 query 를 넘기면
    LangGraph 워크플로우 포트를 호출해 응답을 생성한다.
    """

    def __init__(self, workflow_port: AgentWorkflowPort):
        self._workflow_port = workflow_port

    async def execute(
        self, account_id: int, request: InvestmentDecisionRequest
    ) -> InvestmentDecisionResponse:
        return await self._workflow_port.run(
            account_id=account_id,
            query=request.query,
        )
