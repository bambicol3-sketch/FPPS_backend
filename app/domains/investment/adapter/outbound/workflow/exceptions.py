class InvestmentWorkflowError(Exception):
    """investment 워크플로우 기본 예외."""


class QueryParseError(InvestmentWorkflowError):
    """자연어 질문 파싱 실패."""

    def __init__(self, reason: str, raw: str | None = None):
        suffix = f" raw={raw!r}" if raw else ""
        super().__init__(f"Query parse failed: {reason}{suffix}")
        self.reason = reason
        self.raw = raw
