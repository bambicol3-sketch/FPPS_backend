from pydantic import BaseModel


class InvestmentDecisionResponse(BaseModel):
    """투자 판단 워크플로우 실행 결과."""

    query: str
    answer: str
    iterations: int
    trace: list[str]
