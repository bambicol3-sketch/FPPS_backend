from __future__ import annotations

from typing import Literal, Optional, TypedDict

Intent = Literal[
    "buy_decision",      # 매수 판단
    "sell_decision",     # 매도 판단
    "risk_analysis",     # 리스크 분석
    "outlook",           # 전망 조회
    "news_summary",      # 뉴스 요약
    "general_info",      # 일반 정보
    "unknown",           # 의도 식별 실패
]

RequiredDataType = Literal[
    "news",              # 뉴스
    "financials",        # 재무
    "market_data",       # 시장 데이터(가격/거래량)
    "disclosure",        # 공시
    "youtube",           # YouTube 영상/댓글
    "theme",             # 테마/섹터
]


class CompanyRef(TypedDict, total=False):
    """질문에 언급된 종목 참조 정보."""

    name: str           # 예: "한화에어로스페이스"
    ticker: Optional[str]  # 예: "012450" / 미확정 시 None


class ParsedQuery(TypedDict):
    """자연어 투자 질문을 파싱한 구조화 결과.

    후속 에이전트(Retrieval, Analysis)가 즉시 소비 가능한 형태.
    """

    company: Optional[CompanyRef]           # 미식별 시 None (테마/섹터 질문)
    intent: Intent
    required_data: list[RequiredDataType]
    raw_query: str                          # 원본 질문 텍스트
