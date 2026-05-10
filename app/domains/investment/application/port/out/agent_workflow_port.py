from abc import ABC, abstractmethod

from app.domains.investment.application.response.investment_decision_response import (
    InvestmentDecisionResponse,
)


class AgentWorkflowPort(ABC):
    """투자 판단 멀티 에이전트 워크플로우 실행 포트."""

    @abstractmethod
    async def run(self, account_id: int, query: str) -> InvestmentDecisionResponse:
        pass
