"""LLM 기반 투자 질문 Query Parser.

자연어 질문을 `ParsedQuery` 구조로 변환한다.

- 재시도 2회
- JSON 응답 파싱 실패 시 `QueryParseError` 전파
- company 미식별 → None 으로 표현
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, get_args

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.domains.investment.adapter.outbound.workflow.exceptions import QueryParseError
from app.domains.investment.adapter.outbound.workflow.parsed_query import (
    CompanyRef,
    Intent,
    ParsedQuery,
    RequiredDataType,
)
from app.infrastructure.config.settings import get_settings

_ALLOWED_INTENTS: tuple[str, ...] = get_args(Intent)
_ALLOWED_DATA: tuple[str, ...] = get_args(RequiredDataType)

MAX_RETRIES = 2

SYSTEM_PROMPT = f"""당신은 한국 주식 투자 질문을 구조화된 JSON 으로 변환하는 파서입니다.
사용자의 자연어 질문에서 다음 3가지를 추출하세요:

1. company (object | null):
   - 질문에 특정 종목이 언급되어 있으면 {{"name": "<종목명>", "ticker": "<6자리 숫자 티커 또는 null>"}}
   - 테마/섹터 전반 질문(예: "방산주 전망")이면 null

2. intent (string):
   반드시 다음 중 하나: {", ".join(_ALLOWED_INTENTS)}

3. required_data (array of string):
   다음 값 중 해당되는 항목만 선택: {", ".join(_ALLOWED_DATA)}
   최소 1개 이상 포함하세요.

**출력 형식**: 오직 JSON 객체만, 다른 설명 없이.
예시:
{{"company": {{"name": "한화에어로스페이스", "ticker": "012450"}}, "intent": "buy_decision", "required_data": ["news", "financials", "market_data"]}}
{{"company": null, "intent": "outlook", "required_data": ["news", "theme"]}}
"""


@lru_cache
def _get_parser_llm() -> ChatOpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise QueryParseError("OPENAI_API_KEY 미설정")
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.multi_agent_model,
        temperature=0.0,
        max_tokens=512,
        timeout=settings.multi_agent_request_timeout,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


async def _call_llm(query: str) -> str:
    llm = _get_parser_llm()
    response = await llm.ainvoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"질문: {query}"),
        ]
    )
    content = getattr(response, "content", "")
    if isinstance(content, list):
        content = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return (content or "").strip()


def _validate_and_build(raw_json: str, query: str) -> ParsedQuery:
    try:
        data: Any = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise QueryParseError(f"JSON 디코딩 실패: {exc}", raw=raw_json) from exc

    if not isinstance(data, dict):
        raise QueryParseError("최상위는 객체여야 함", raw=raw_json)

    # company
    raw_company = data.get("company")
    company: CompanyRef | None
    if raw_company is None:
        company = None
    elif isinstance(raw_company, dict):
        name = raw_company.get("name")
        if not isinstance(name, str) or not name.strip():
            raise QueryParseError("company.name 누락", raw=raw_json)
        ticker_raw = raw_company.get("ticker")
        ticker: str | None
        if ticker_raw is None or ticker_raw == "":
            ticker = None
        elif isinstance(ticker_raw, str):
            ticker = ticker_raw.strip() or None
        else:
            ticker = str(ticker_raw)
        company = CompanyRef(name=name.strip(), ticker=ticker)
    else:
        raise QueryParseError("company 는 null 또는 object 여야 함", raw=raw_json)

    # intent
    intent_raw = data.get("intent")
    if not isinstance(intent_raw, str) or intent_raw not in _ALLOWED_INTENTS:
        raise QueryParseError(
            f"intent 값이 허용 목록에 없음: {intent_raw!r}",
            raw=raw_json,
        )

    # required_data
    required_raw = data.get("required_data")
    if not isinstance(required_raw, list) or not required_raw:
        raise QueryParseError("required_data 는 비어있지 않은 배열이어야 함", raw=raw_json)
    required_data: list[RequiredDataType] = []
    for item in required_raw:
        if not isinstance(item, str) or item not in _ALLOWED_DATA:
            raise QueryParseError(
                f"required_data 항목이 허용 목록에 없음: {item!r}",
                raw=raw_json,
            )
        if item not in required_data:
            required_data.append(item)  # type: ignore[arg-type]

    return ParsedQuery(
        company=company,
        intent=intent_raw,  # type: ignore[typeddict-item]
        required_data=required_data,
        raw_query=query,
    )


async def parse_investment_query(query: str) -> ParsedQuery:
    """자연어 투자 질문을 구조화된 `ParsedQuery` 로 변환한다.

    Args:
        query: 사용자 자연어 질문

    Raises:
        QueryParseError: LLM 응답이 JSON 포맷 오류이거나 검증 실패할 때
    """
    if not query or not query.strip():
        raise QueryParseError("빈 질문")

    clean = query.strip()
    print(f"[investment.query_parser] start query={clean[:80]!r}", flush=True)

    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 2):  # 1 + MAX_RETRIES 시도
        try:
            raw_json = await _call_llm(clean)
            print(
                f"[investment.query_parser] attempt={attempt} raw={raw_json[:120]!r}",
                flush=True,
            )
            parsed = _validate_and_build(raw_json, clean)
            print(
                f"[investment.query_parser] success attempt={attempt} "
                f"company={parsed['company']!r} intent={parsed['intent']} "
                f"required_data={parsed['required_data']}",
                flush=True,
            )
            return parsed
        except QueryParseError as exc:
            last_err = exc
            print(
                f"[investment.query_parser] attempt={attempt} 실패: {exc}",
                flush=True,
            )
            if attempt > MAX_RETRIES:
                break
        except Exception as exc:  # LLM 호출 자체 실패
            last_err = exc
            print(
                f"[investment.query_parser] LLM 호출 실패 attempt={attempt}: {exc}",
                flush=True,
            )
            if attempt > MAX_RETRIES:
                break

    raise QueryParseError(
        reason=f"{MAX_RETRIES + 1}회 시도 모두 실패: {last_err}",
        raw=clean,
    )
