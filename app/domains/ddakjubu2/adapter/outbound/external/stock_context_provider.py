from datetime import datetime, timezone
from typing import List, Optional

from app.domains.ddakjubu2.application.port.stock_context_provider_port import (
    StockContextProviderPort,
)
from app.domains.stock.adapter.outbound.external.opendart_financial_data_provider import (
    OpenDartFinancialDataProvider,
)
from app.domains.stock.adapter.outbound.external.serp_stock_data_collector import (
    SerpStockDataCollector,
)
from app.domains.stock.adapter.outbound.persistence.corp_code_repository_impl import (
    CorpCodeRepositoryImpl,
)
from app.domains.stock.infrastructure.mapper.serp_stock_data_standardizer import (
    SerpStockDataStandardizer,
)


class StockContextProvider(StockContextProviderPort):
    """SerpAPI(구글 파이낸스) + DART 재무비율을 합성해 종목 데이터 컨텍스트를 만든다.

    수급/차트(OHLCV) 데이터 소스는 아직 없으므로 컨텍스트에 명시적으로
    '제공되지 않음' 을 남겨 LLM 이 missing_data 로 처리하게 한다.
    """

    def __init__(self, serp_api_key: str, dart_api_key: str):
        self._serp_collector = (
            SerpStockDataCollector(api_key=serp_api_key) if serp_api_key else None
        )
        self._standardizer = SerpStockDataStandardizer()
        self._corp_code_repository = CorpCodeRepositoryImpl()
        self._dart_provider = (
            OpenDartFinancialDataProvider(api_key=dart_api_key)
            if dart_api_key
            else None
        )

    async def build_context(
        self, ticker: str, stock_name: str, market: str
    ) -> str:
        as_of = datetime.now(timezone.utc).isoformat()
        sections: List[str] = [
            f"조회 시점: {as_of}",
            f"종목: {stock_name} ({ticker}, {market or 'KRX'})",
            "",
        ]
        sections.append(await self._build_price_section(ticker, stock_name, market))
        sections.append("")
        sections.append(await self._build_dart_section(ticker))
        sections.append("")
        sections.append(
            "## 수급/차트 데이터\n"
            "외국인/기관 수급, 일봉/주봉 차트, 가격 밴드 데이터는 제공되지 않음."
        )
        return "\n".join(sections)

    async def _build_price_section(
        self, ticker: str, stock_name: str, market: str
    ) -> str:
        header = "## 시세/밸류에이션 (Google Finance)"
        if self._serp_collector is None:
            return f"{header}\n제공되지 않음 (SerpAPI 미설정)."
        try:
            raw = await self._serp_collector.collect(
                ticker=ticker, stock_name=stock_name, market=market or "KOSPI"
            )
            if raw is None:
                return f"{header}\n조회 실패 — 제공되지 않음."
            data = self._standardizer.standardize(raw)
            if data is None:
                return f"{header}\n표준화 실패 — 제공되지 않음."
            lines = [header]
            lines.append(f"- 현재가: {self._fmt(data.current_price)} {data.currency or ''}")
            lines.append(f"- 시가총액: {self._fmt(data.market_cap)}")
            lines.append(f"- PER: {self._fmt(data.pe_ratio)}")
            lines.append(f"- 배당수익률: {self._fmt(data.dividend_yield)}")
            if data.company_summary:
                lines.append(f"- 기업 개요: {data.company_summary[:300]}")
            return "\n".join(lines)
        except Exception as e:
            print(f"[ddakjubu2_apply] Serp 시세 조회 실패 ticker={ticker} error={e}")
            return f"{header}\n조회 실패 — 제공되지 않음."

    async def _build_dart_section(self, ticker: str) -> str:
        header = "## 재무비율 (DART, 최근 사업연도)"
        if self._dart_provider is None:
            return f"{header}\n제공되지 않음 (DART API 미설정)."
        try:
            mapping = await self._corp_code_repository.find_by_ticker(ticker)
            if mapping is None:
                return f"{header}\nDART 고유번호 매핑 없음 — 제공되지 않음."
            ratios = None
            for year_offset in (1, 2):
                fiscal_year = str(datetime.now().year - year_offset)
                ratios = await self._dart_provider.fetch_financial_ratios(
                    corp_code=mapping.corp_code, fiscal_year=fiscal_year
                )
                if ratios is not None:
                    break
            if ratios is None:
                return f"{header}\n조회 실패 — 제공되지 않음."
            lines = [header, f"- 사업연도: {ratios.fiscal_year}"]
            lines.append(f"- ROE: {self._fmt_num(ratios.roe, '%')}")
            lines.append(f"- ROA: {self._fmt_num(ratios.roa, '%')}")
            lines.append(f"- 부채비율: {self._fmt_num(ratios.debt_ratio, '%')}")
            lines.append(f"- 매출액: {self._fmt_num(ratios.sales, '원')}")
            lines.append(f"- 영업이익: {self._fmt_num(ratios.operating_income, '원')}")
            lines.append(f"- 당기순이익: {self._fmt_num(ratios.net_income, '원')}")
            if ratios.prev_sales is not None:
                lines.append(f"- 전기 매출액: {self._fmt_num(ratios.prev_sales, '원')}")
            if ratios.prev_operating_income is not None:
                lines.append(
                    f"- 전기 영업이익: {self._fmt_num(ratios.prev_operating_income, '원')}"
                )
            if ratios.prev_net_income is not None:
                lines.append(
                    f"- 전기 당기순이익: {self._fmt_num(ratios.prev_net_income, '원')}"
                )
            return "\n".join(lines)
        except Exception as e:
            print(f"[ddakjubu2_apply] DART 조회 실패 ticker={ticker} error={e}")
            return f"{header}\n조회 실패 — 제공되지 않음."

    @staticmethod
    def _fmt(value: Optional[str]) -> str:
        return value if value else "제공되지 않음"

    @staticmethod
    def _fmt_num(value: Optional[float], unit: str) -> str:
        if value is None:
            return "제공되지 않음"
        return f"{value:,.2f}{unit}" if unit == "%" else f"{value:,.0f}{unit}"
