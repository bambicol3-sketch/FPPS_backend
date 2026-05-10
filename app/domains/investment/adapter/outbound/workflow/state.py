from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from app.domains.investment.adapter.outbound.workflow.parsed_query import ParsedQuery

NextAgent = Literal["retrieval", "analysis", "synthesis", "end"]


class InvestmentAgentState(TypedDict, total=False):
    """투자 판단 워크플로우 공유 State.

    - query: 사용자의 투자 관련 질문
    - account_id: 인증된 사용자 ID
    - parsed_query: Orchestrator 가 호출한 Query Parser 결과 (company/intent/required_data)
    - next_agent: Orchestrator 가 결정한 다음 실행 Agent
    - retrieval_data: Retrieval Agent 가 수집한 원천 데이터
    - analysis_insight: Analysis Agent 가 생성한 인사이트
    - synthesis_answer: Synthesis Agent 가 생성한 최종 응답
    - iteration: 현재 Orchestrator 라우팅 반복 횟수 (루프 방지)
    - trace: 노드 실행 로그 (append-only)
    - error: 실행 도중 발생한 오류 메시지
    """

    query: str
    account_id: int
    parsed_query: ParsedQuery
    next_agent: NextAgent
    retrieval_data: dict[str, Any]
    analysis_insight: dict[str, Any]
    synthesis_answer: str
    iteration: int
    trace: Annotated[list[str], operator.add]
    error: str
