from datetime import datetime, timezone
from typing import List, Optional

from app.domains.ddakjubu2.adapter.outbound.external.stock_context_provider import (
    StockContextProvider,
)
from app.domains.frontier_agent.application.port.frontier_ports import FrontierToolPort
from app.domains.frontier_agent.domain.entity.analysis_run import ToolEvidence


class StockDataTool(FrontierToolPort):
    """종목 시세·밸류에이션(SerpAPI/Google Finance)·재무비율(DART) 도구.

    ddakjubu2 의 StockContextProvider 를 재사용해 텍스트 컨텍스트를 얻는다.
    """

    name = "stock_data"
    description = "종목 시세·시가총액·PER·배당(SerpAPI) 및 ROE·부채비율 등 재무(DART)"

    def __init__(self, serp_api_key: str, dart_api_key: str):
        self._provider = StockContextProvider(
            serp_api_key=serp_api_key, dart_api_key=dart_api_key
        )

    def applies(self, question: str, ticker: Optional[str]) -> bool:
        return bool(ticker)

    async def gather(
        self, question: str, ticker: Optional[str], stock_name: Optional[str]
    ) -> List[ToolEvidence]:
        if not ticker:
            return []
        context = await self._provider.build_context(
            ticker=ticker, stock_name=stock_name or ticker, market="KOSPI"
        )
        return [
            ToolEvidence(
                tool=self.name,
                source_institution="SerpAPI/Google Finance + DART",
                data_origin="거래소 시세·기업 재무제표",
                collected_by="SerpAPI 집계 / 금융감독원 DART 접수",
                publish_method="실시간 시세 / 사업연도별 공시",
                content=context,
                available=True,
                retrieved_at=datetime.now(timezone.utc),
            )
        ]
