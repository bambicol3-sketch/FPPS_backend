from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

MessageRole = Literal["system", "user", "assistant", "planner", "researcher", "analyst", "reviewer"]


class AgentMessage(TypedDict):
    """그래프 내부를 흐르는 단일 메시지."""

    role: MessageRole
    node: str
    content: str


class AgentState(TypedDict, total=False):
    """멀티 에이전트 그래프의 공통 실행 컨텍스트.

    - query: 최초 사용자 입력
    - messages: 노드 간 주고받은 메시지 이력 (append-only, reducer=operator.add)
    - memory: 노드가 공유하는 키-값 스크래치패드
    - plan: Planner가 만든 실행 계획
    - research: Researcher가 수집한 자료
    - analysis: Analyst가 도출한 분석
    - review: Reviewer의 품질 검토 결과
    - final_answer: 그래프 최종 응답
    - step_count: 현재까지 실행된 노드 수 (무한 루프 방지)
    - error: 실행 도중 발생한 오류 메시지
    """

    query: str
    messages: Annotated[list[AgentMessage], operator.add]
    memory: dict[str, Any]
    plan: str
    research: str
    analysis: str
    review: str
    final_answer: str
    step_count: int
    error: str
