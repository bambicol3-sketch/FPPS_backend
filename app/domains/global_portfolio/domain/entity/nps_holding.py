from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

NpsMarket = Literal["domestic", "overseas"]


@dataclass(frozen=True)
class NpsHolding:
    """국민연금공단 주요 보유종목 (단일 종목)."""

    market: NpsMarket   # "domestic" | "overseas"
    ticker: str         # 종목코드 또는 티커 (예: 005930, AAPL)
    name: str           # 종목명
    country: str        # 국가 (한국, 미국 등)
    sector: str         # 업종
    shares: int | None  # 보유 주수 (공개된 경우)
    value_krw_bn: float | None  # 보유금액 (억원 기준, 공개된 경우)
    weight_pct: float | None    # 포트폴리오 비중 (%)
    note: str = ""
