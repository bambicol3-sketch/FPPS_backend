"""투자 판단 멀티 에이전트 노드.

이 파일은 백로그 DSAIS-51 에 따라 '흐름만' 구성한다.
각 Agent 의 상세 로직(LLM 프롬프트, 외부 API 호출)은 후속 스토리에서 채운다.

추적 출력은 모두 print() 로만 내보낸다 (콘솔 가시성 목적).
"""
from typing import Any

from app.domains.investment.adapter.outbound.workflow.query_parser import (
    parse_investment_query,
)
from app.domains.investment.adapter.outbound.workflow.state import (
    InvestmentAgentState,
    NextAgent,
)

DISCLAIMER = (
    "※ 본 응답은 투자 권유가 아닌 정보 제공 목적이며, "
    "최종 투자 결정과 책임은 투자자 본인에게 있습니다."
)


def _log(node: str, message: str) -> None:
    print(f"[investment.{node}] {message}", flush=True)


# ─────────────────────────────────────────────────────────────
# Orchestrator Agent
# ─────────────────────────────────────────────────────────────
async def orchestrator_node(state: InvestmentAgentState) -> dict:
    """상태 기반으로 다음 실행 Agent 를 결정한다.

    흐름:
        0. parsed_query 없음 → Query Parser 호출 후 State 에 기록
        1. retrieval_data 없음 → retrieval
        2. analysis_insight 없음 → analysis
        3. synthesis_answer 없음 → synthesis
        4. 모두 있음 → end

    Query Parser 실패 시 `QueryParseError` 가 상위로 전파된다.
    """
    iteration = state.get("iteration", 0) + 1
    query = state.get("query", "")
    _log("orchestrator", f"enter iteration={iteration} query={query[:60]!r}")

    updates: dict[str, Any] = {}
    trace_lines: list[str] = []

    # 첫 진입 시 Query Parser 1회 호출
    parsed = state.get("parsed_query")
    if parsed is None:
        _log("orchestrator", "parsed_query 없음 → Query Parser 호출")
        parsed = await parse_investment_query(query)
        updates["parsed_query"] = parsed
        company_name = (parsed.get("company") or {}).get("name") if parsed.get("company") else None
        trace_lines.append(
            f"query_parser -> company={company_name!r} "
            f"intent={parsed['intent']} required_data={parsed['required_data']}"
        )
        _log(
            "orchestrator",
            f"query parsed company={company_name!r} intent={parsed['intent']} "
            f"required_data={parsed['required_data']}",
        )

    next_agent: NextAgent
    if not state.get("retrieval_data"):
        next_agent = "retrieval"
    elif not state.get("analysis_insight"):
        next_agent = "analysis"
    elif not state.get("synthesis_answer"):
        next_agent = "synthesis"
    else:
        next_agent = "end"

    _log("orchestrator", f"decided next_agent={next_agent}")
    trace_lines.append(f"orchestrator -> {next_agent} (iter={iteration})")
    updates["next_agent"] = next_agent
    updates["iteration"] = iteration
    updates["trace"] = trace_lines
    return updates


# ─────────────────────────────────────────────────────────────
# Retrieval Agent
# ─────────────────────────────────────────────────────────────
def retrieval_node(state: InvestmentAgentState) -> dict:
    """투자 관련 원천 데이터를 수집한다 (스켈레톤).

    실제 구현 시:
        - SERP 뉴스 검색 (SerpNewsSearchProvider)
        - 저장된 관심 기사 조회 (UserSavedArticleRepository)
        - YouTube API (YoutubeVideoClient)
        - 종목/시장 정보 (StockRepository)
    """
    _log("retrieval", f"enter query={state.get('query', '')[:60]!r}")

    # TODO(DSAIS-52+): 외부 소스 수집 실제 구현
    collected: dict[str, Any] = {
        "news": [],        # SERP / saved articles
        "videos": [],      # YouTube API
        "stock_info": {},  # 종목/시장 정보
        "note": "skeleton — not yet populated",
    }

    _log("retrieval", f"exit collected_keys={list(collected.keys())}")
    return {
        "retrieval_data": collected,
        "trace": ["retrieval collected (skeleton)"],
    }


# ─────────────────────────────────────────────────────────────
# Analysis Agent
# ─────────────────────────────────────────────────────────────
def analysis_node(state: InvestmentAgentState) -> dict:
    """수집 데이터로 종목 전망/리스크/포인트 인사이트를 생성한다 (스켈레톤).

    실제 구현 시:
        - LLM 프롬프트 체인 (ChatOpenAI)
        - 키워드 / 감성 분석
        - RAG 검색 결합
    """
    _log("analysis", "enter with retrieval_data")

    # TODO(DSAIS-52+): 실제 분석 LLM 체인 연결
    insight: dict[str, Any] = {
        "outlook": "(skeleton) 종목 전망 미구현",
        "risks": [],
        "points": [],
    }

    _log("analysis", f"exit insight_keys={list(insight.keys())}")
    return {
        "analysis_insight": insight,
        "trace": ["analysis insight generated (skeleton)"],
    }


# ─────────────────────────────────────────────────────────────
# Synthesis Agent
# ─────────────────────────────────────────────────────────────
def synthesis_node(state: InvestmentAgentState) -> dict:
    """분석 결과를 사용자 응답으로 종합한다.

    최종 응답에는 투자 권유가 아닌 정보 제공임을 명시하는
    면책 문구(DISCLAIMER) 를 반드시 포함한다.
    """
    _log("synthesis", "enter with analysis_insight")
    query = state.get("query", "")
    insight = state.get("analysis_insight") or {}

    # TODO(DSAIS-52+): LLM 기반 자연어 합성
    body = (
        f"[질문] {query}\n"
        f"[전망] {insight.get('outlook', '(미구현)')}\n"
        f"[리스크] {', '.join(insight.get('risks') or ['(미구현)'])}\n"
        f"[포인트] {', '.join(insight.get('points') or ['(미구현)'])}"
    )
    answer = f"{body}\n\n{DISCLAIMER}"

    _log("synthesis", f"exit answer_chars={len(answer)}")
    return {
        "synthesis_answer": answer,
        "trace": ["synthesis answer composed (skeleton)"],
    }
