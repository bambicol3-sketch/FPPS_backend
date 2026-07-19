import re
import time
from typing import List, Optional, Tuple

from app.domains.frontier_agent.adapter.outbound.external.frontier_orchestrator import (
    FrontierOrchestrator,
)
from app.domains.frontier_agent.application.port.frontier_ports import (
    FrontierAnalysisRepositoryPort,
    FrontierAuditRepositoryPort,
)
from app.domains.frontier_agent.application.request.frontier_requests import (
    AnalyzeRequest,
)
from app.domains.frontier_agent.application.response.frontier_responses import (
    FrontierAnalysisResponse,
    ReasoningStepDto,
    ToolEvidenceDto,
)
from app.domains.frontier_agent.domain.entity.analysis_run import FrontierAnalysis
from app.domains.stock.application.port.stock_repository import StockRepository

TICKER_PATTERN = re.compile(r"^\d{6}$")


def analysis_to_response(analysis: FrontierAnalysis) -> FrontierAnalysisResponse:
    return FrontierAnalysisResponse(
        run_id=analysis.run_id,
        question=analysis.question,
        ticker=analysis.ticker,
        stock_name=analysis.stock_name,
        plan=analysis.plan,
        answer=analysis.answer,
        confidence=analysis.confidence,
        steps=[
            ReasoningStepDto(node=s.node, content=s.content, attempt=s.attempt)
            for s in analysis.steps
        ],
        evidences=[
            ToolEvidenceDto(
                tool=e.tool,
                source_institution=e.source_institution,
                data_origin=e.data_origin,
                collected_by=e.collected_by,
                publish_method=e.publish_method,
                content=e.content,
                available=e.available,
            )
            for e in analysis.evidences
        ],
        missing_data=analysis.missing_data,
        caveats=analysis.caveats,
        revised_count=analysis.revised_count,
        refused=analysis.refused,
        analyzed_at=analysis.analyzed_at,
    )


class RunFrontierAnalysisUseCase:
    def __init__(
        self,
        orchestrator: FrontierOrchestrator,
        analysis_repository_port: FrontierAnalysisRepositoryPort,
        audit_repository_port: FrontierAuditRepositoryPort,
        stock_repository: Optional[StockRepository] = None,
    ):
        self._orchestrator = orchestrator
        self._analysis_repository_port = analysis_repository_port
        self._audit_repository_port = audit_repository_port
        self._stock_repository = stock_repository

    async def execute(self, request: AnalyzeRequest) -> FrontierAnalysisResponse:
        started = time.monotonic()
        ticker, stock_name = await self._resolve_stock(request.stock_input)

        analysis = await self._orchestrator.run(
            question=request.question, ticker=ticker, stock_name=stock_name
        )

        latency_ms = int((time.monotonic() - started) * 1000)
        tools_used = sorted({e.tool for e in analysis.evidences})

        try:
            await self._analysis_repository_port.save(analysis)
        except Exception as e:
            print(f"[frontier] 분석 저장 실패: {e}", flush=True)
        try:
            await self._audit_repository_port.save(
                run_id=analysis.run_id,
                question=analysis.question,
                ticker=analysis.ticker,
                answer=analysis.answer,
                confidence=analysis.confidence,
                tools_used=tools_used,
                revised_count=analysis.revised_count,
                refused=analysis.refused,
                latency_ms=latency_ms,
            )
        except Exception as e:
            print(f"[frontier] 감사 로그 저장 실패: {e}", flush=True)

        return analysis_to_response(analysis)

    async def _resolve_stock(
        self, stock_input: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        query = (stock_input or "").strip()
        if not query:
            return None, None
        # 6자리 코드는 repo 없이도 그대로 티커로 사용
        if TICKER_PATTERN.match(query):
            if self._stock_repository is not None:
                stock = await self._stock_repository.find_by_ticker(query)
                if stock is not None:
                    return stock.ticker, stock.stock_name
            return query, query
        if self._stock_repository is not None:
            stock = await self._stock_repository.find_by_company_name(query)
            if stock is not None:
                return stock.ticker, stock.stock_name
        # 이름 해석 실패 시에도 종목 비특정으로 계속(거부 대신 방법론/일반 분석)
        return None, None


class GetFrontierHistoryUseCase:
    def __init__(self, analysis_repository_port: FrontierAnalysisRepositoryPort):
        self._analysis_repository_port = analysis_repository_port

    async def execute(
        self, ticker: Optional[str], limit: int
    ) -> List[FrontierAnalysisResponse]:
        analyses = await self._analysis_repository_port.find_history(ticker, limit)
        return [analysis_to_response(a) for a in analyses]
