from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class SemiconductorCompany:
    ticker: str
    name: str
    segment: str  # 메모리/파운드리/소재/장비 등

    _KR_COMPANIES: ClassVar[list["SemiconductorCompany"]] = []

    @classmethod
    def kr_companies(cls) -> list["SemiconductorCompany"]:
        return [
            cls("005930", "삼성전자", "메모리/파운드리"),
            cls("000660", "SK하이닉스", "메모리"),
            cls("000990", "DB하이텍", "파운드리"),
            cls("042700", "한미반도체", "장비"),
            cls("240810", "원익IPS", "장비"),
            cls("036540", "SFA반도체", "패키징"),
            cls("046890", "서울반도체", "LED/광반도체"),
            cls("009520", "포스코DX", "스마트팩토리"),
            cls("033640", "네패스", "패키징"),
            cls("178920", "PI첨단소재", "소재"),
        ]

    @classmethod
    def find_by_ticker(cls, ticker: str) -> "SemiconductorCompany | None":
        return next((c for c in cls.kr_companies() if c.ticker == ticker), None)
