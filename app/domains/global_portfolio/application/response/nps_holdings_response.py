from __future__ import annotations

from pydantic import BaseModel

from app.domains.global_portfolio.domain.entity.nps_holding import NpsHolding


class NpsHoldingItem(BaseModel):
    market: str
    ticker: str
    name: str
    country: str
    sector: str
    shares: int | None
    value_krw_bn: float | None
    weight_pct: float | None
    note: str

    @classmethod
    def from_entity(cls, entity: NpsHolding) -> "NpsHoldingItem":
        return cls(
            market=entity.market,
            ticker=entity.ticker,
            name=entity.name,
            country=entity.country,
            sector=entity.sector,
            shares=entity.shares,
            value_krw_bn=entity.value_krw_bn,
            weight_pct=entity.weight_pct,
            note=entity.note,
        )


class NpsHoldingsResponse(BaseModel):
    domestic: list[NpsHoldingItem]
    overseas: list[NpsHoldingItem]
    total_count: int
    data_as_of: str = "2024-2025 공시 기준 (분기 갱신)"
