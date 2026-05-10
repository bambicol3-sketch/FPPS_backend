class MultiAgentError(Exception):
    """멀티 에이전트 인프라 기본 예외."""


class LLMInvocationError(MultiAgentError):
    """LLM 호출(OpenAI 등) 실패."""

    def __init__(self, node: str, reason: str):
        super().__init__(f"LLM 호출 실패 (node={node}): {reason}")
        self.node = node
        self.reason = reason


class GraphExecutionError(MultiAgentError):
    """그래프 실행 중 발생한 치명적 오류."""

    def __init__(self, node: str, reason: str):
        super().__init__(f"그래프 실행 실패 (node={node}): {reason}")
        self.node = node
        self.reason = reason
