"""국민연금공단 주요 보유종목 정적 데이터 제공자.

NPS는 5%+ 국내 지분 공시(DART) 및 분기별 포트폴리오 공시를 통해
보유종목을 공개한다. 아래 데이터는 2024~2025년 공시·언론 보도 기준
주요 보유종목을 정리한 것이다.

국내: KRX 상장 주식 (종목코드 6자리)
해외: 미국 상장 주식 (NYSE/NASDAQ 티커)
"""

from __future__ import annotations

from app.domains.global_portfolio.domain.entity.nps_holding import NpsHolding, NpsMarket


def get_nps_holdings(market: NpsMarket | None = None) -> list[NpsHolding]:
    """NPS 보유종목 전체 목록을 반환한다. market 필터 지정 가능."""
    holdings = _DOMESTIC_HOLDINGS + _OVERSEAS_HOLDINGS
    if market is None:
        return holdings
    return [h for h in holdings if h.market == market]


# ── 국내 보유종목 (2024-2025 공시 기준) ──────────────────────────────────────

_DOMESTIC_HOLDINGS: list[NpsHolding] = [
    NpsHolding(
        market="domestic", ticker="005930", name="삼성전자",
        country="한국", sector="반도체/전자",
        shares=None, value_krw_bn=None, weight_pct=7.2,
        note="국내 최대 비중 보유종목 / 5% 이상 지분 공시",
    ),
    NpsHolding(
        market="domestic", ticker="000660", name="SK하이닉스",
        country="한국", sector="반도체",
        shares=None, value_krw_bn=None, weight_pct=3.1,
        note="HBM 생산 확대로 비중 증가",
    ),
    NpsHolding(
        market="domestic", ticker="005380", name="현대자동차",
        country="한국", sector="자동차",
        shares=None, value_krw_bn=None, weight_pct=2.4,
        note="전기차 전환 모멘텀 보유",
    ),
    NpsHolding(
        market="domestic", ticker="035420", name="NAVER",
        country="한국", sector="인터넷/플랫폼",
        shares=None, value_krw_bn=None, weight_pct=1.9,
    ),
    NpsHolding(
        market="domestic", ticker="051910", name="LG화학",
        country="한국", sector="화학/이차전지",
        shares=None, value_krw_bn=None, weight_pct=1.7,
    ),
    NpsHolding(
        market="domestic", ticker="006400", name="삼성SDI",
        country="한국", sector="이차전지",
        shares=None, value_krw_bn=None, weight_pct=1.5,
    ),
    NpsHolding(
        market="domestic", ticker="035720", name="카카오",
        country="한국", sector="인터넷/플랫폼",
        shares=None, value_krw_bn=None, weight_pct=1.3,
    ),
    NpsHolding(
        market="domestic", ticker="207940", name="삼성바이오로직스",
        country="한국", sector="바이오/제약",
        shares=None, value_krw_bn=None, weight_pct=1.2,
    ),
    NpsHolding(
        market="domestic", ticker="000270", name="기아",
        country="한국", sector="자동차",
        shares=None, value_krw_bn=None, weight_pct=1.2,
    ),
    NpsHolding(
        market="domestic", ticker="373220", name="LG에너지솔루션",
        country="한국", sector="이차전지",
        shares=None, value_krw_bn=None, weight_pct=1.1,
    ),
    NpsHolding(
        market="domestic", ticker="030200", name="KT",
        country="한국", sector="통신",
        shares=None, value_krw_bn=None, weight_pct=0.9,
    ),
    NpsHolding(
        market="domestic", ticker="032830", name="삼성생명",
        country="한국", sector="금융/보험",
        shares=None, value_krw_bn=None, weight_pct=0.8,
    ),
    NpsHolding(
        market="domestic", ticker="055550", name="신한지주",
        country="한국", sector="금융/은행",
        shares=None, value_krw_bn=None, weight_pct=0.8,
    ),
    NpsHolding(
        market="domestic", ticker="105560", name="KB금융",
        country="한국", sector="금융/은행",
        shares=None, value_krw_bn=None, weight_pct=0.8,
    ),
    NpsHolding(
        market="domestic", ticker="096770", name="SK이노베이션",
        country="한국", sector="에너지/화학",
        shares=None, value_krw_bn=None, weight_pct=0.7,
    ),
]

# ── 해외 보유종목 — 미국 상장 주식 (2024-2025 기준) ──────────────────────────

_OVERSEAS_HOLDINGS: list[NpsHolding] = [
    NpsHolding(
        market="overseas", ticker="AAPL", name="Apple Inc.",
        country="미국", sector="기술/소비자가전",
        shares=None, value_krw_bn=None, weight_pct=2.1,
        note="미국 대형 기술주 최대 보유",
    ),
    NpsHolding(
        market="overseas", ticker="MSFT", name="Microsoft Corp.",
        country="미국", sector="기술/클라우드",
        shares=None, value_krw_bn=None, weight_pct=1.9,
    ),
    NpsHolding(
        market="overseas", ticker="NVDA", name="NVIDIA Corp.",
        country="미국", sector="반도체/AI",
        shares=None, value_krw_bn=None, weight_pct=1.7,
        note="AI 열풍 수혜로 비중 증가",
    ),
    NpsHolding(
        market="overseas", ticker="AMZN", name="Amazon.com Inc.",
        country="미국", sector="전자상거래/클라우드",
        shares=None, value_krw_bn=None, weight_pct=1.4,
    ),
    NpsHolding(
        market="overseas", ticker="GOOGL", name="Alphabet Inc. (Class A)",
        country="미국", sector="인터넷/광고",
        shares=None, value_krw_bn=None, weight_pct=1.2,
    ),
    NpsHolding(
        market="overseas", ticker="META", name="Meta Platforms Inc.",
        country="미국", sector="소셜미디어/광고",
        shares=None, value_krw_bn=None, weight_pct=1.0,
    ),
    NpsHolding(
        market="overseas", ticker="TSLA", name="Tesla Inc.",
        country="미국", sector="전기차/에너지",
        shares=None, value_krw_bn=None, weight_pct=0.8,
    ),
    NpsHolding(
        market="overseas", ticker="BRK.B", name="Berkshire Hathaway Inc.",
        country="미국", sector="금융/복합",
        shares=None, value_krw_bn=None, weight_pct=0.7,
    ),
    NpsHolding(
        market="overseas", ticker="JNJ", name="Johnson & Johnson",
        country="미국", sector="헬스케어/제약",
        shares=None, value_krw_bn=None, weight_pct=0.6,
    ),
    NpsHolding(
        market="overseas", ticker="XOM", name="Exxon Mobil Corp.",
        country="미국", sector="에너지/석유",
        shares=None, value_krw_bn=None, weight_pct=0.6,
    ),
    NpsHolding(
        market="overseas", ticker="JPM", name="JPMorgan Chase & Co.",
        country="미국", sector="금융/은행",
        shares=None, value_krw_bn=None, weight_pct=0.5,
    ),
    NpsHolding(
        market="overseas", ticker="V", name="Visa Inc.",
        country="미국", sector="금융/결제",
        shares=None, value_krw_bn=None, weight_pct=0.5,
    ),
    NpsHolding(
        market="overseas", ticker="UNH", name="UnitedHealth Group Inc.",
        country="미국", sector="헬스케어/보험",
        shares=None, value_krw_bn=None, weight_pct=0.4,
    ),
    NpsHolding(
        market="overseas", ticker="MA", name="Mastercard Inc.",
        country="미국", sector="금융/결제",
        shares=None, value_krw_bn=None, weight_pct=0.4,
    ),
    NpsHolding(
        market="overseas", ticker="PG", name="Procter & Gamble Co.",
        country="미국", sector="생활용품",
        shares=None, value_krw_bn=None, weight_pct=0.4,
    ),
    NpsHolding(
        market="overseas", ticker="HD", name="The Home Depot Inc.",
        country="미국", sector="소매/건자재",
        shares=None, value_krw_bn=None, weight_pct=0.3,
    ),
    NpsHolding(
        market="overseas", ticker="CVX", name="Chevron Corp.",
        country="미국", sector="에너지/석유",
        shares=None, value_krw_bn=None, weight_pct=0.3,
    ),
    NpsHolding(
        market="overseas", ticker="ABBV", name="AbbVie Inc.",
        country="미국", sector="바이오/제약",
        shares=None, value_krw_bn=None, weight_pct=0.3,
    ),
    NpsHolding(
        market="overseas", ticker="LLY", name="Eli Lilly and Company",
        country="미국", sector="제약/바이오",
        shares=None, value_krw_bn=None, weight_pct=0.3,
        note="GLP-1 비만치료제 성장세",
    ),
    NpsHolding(
        market="overseas", ticker="AVGO", name="Broadcom Inc.",
        country="미국", sector="반도체/네트워크",
        shares=None, value_krw_bn=None, weight_pct=0.3,
    ),
]
