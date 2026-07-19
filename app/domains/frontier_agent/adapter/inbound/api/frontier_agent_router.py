from typing import Optional

from fastapi import APIRouter, Query

from app.common.response.base_response import BaseResponse
from app.domains.frontier_agent.adapter.outbound.external.frontier_llm_client import (
    OpenAICompatibleFrontierLlm,
)
from app.domains.frontier_agent.adapter.outbound.external.frontier_orchestrator import (
    FrontierOrchestrator,
)
from app.domains.frontier_agent.adapter.outbound.persistence.frontier_repositories import (
    FrontierAnalysisRepositoryImpl,
    FrontierAuditRepositoryImpl,
)
from app.domains.frontier_agent.application.request.frontier_requests import (
    AnalyzeRequest,
)
from app.domains.frontier_agent.application.tool.fx_flow_tool import FxFlowTool
from app.domains.frontier_agent.application.tool.methodology_tool import MethodologyTool
from app.domains.frontier_agent.application.tool.stock_data_tool import StockDataTool
from app.domains.frontier_agent.application.usecase.run_frontier_analysis_usecase import (
    GetFrontierHistoryUseCase,
    RunFrontierAnalysisUseCase,
)
from app.domains.ddakjubu2.adapter.outbound.persistence.methodology_repository_impl import (
    MethodologyRepositoryImpl,
)
from app.domains.stock.adapter.outbound.persistence.stock_repository_impl import (
    StockRepositoryImpl,
)
from app.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/frontier-agent", tags=["frontier-agent"])


def _build_orchestrator(settings) -> FrontierOrchestrator:
    tools = [
        StockDataTool(
            serp_api_key=settings.serp_api_key,
            dart_api_key=settings.open_dart_api_key or settings.dart_api_key,
        ),
        MethodologyTool(
            methodology_repository_port=MethodologyRepositoryImpl()
        ),
        FxFlowTool(),
    ]
    llm = OpenAICompatibleFrontierLlm(
        api_key=settings.frontier_llm_api_key or settings.openai_api_key,
        model=settings.frontier_llm_model,
        base_url=settings.frontier_llm_base_url,
    )
    return FrontierOrchestrator(
        llm_port=llm,
        tools=tools,
        max_revisions=settings.frontier_max_revisions,
    )


@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    settings = get_settings()
    usecase = RunFrontierAnalysisUseCase(
        orchestrator=_build_orchestrator(settings),
        analysis_repository_port=FrontierAnalysisRepositoryImpl(),
        audit_repository_port=FrontierAuditRepositoryImpl(),
        stock_repository=StockRepositoryImpl(),
    )
    response = await usecase.execute(request)
    return BaseResponse.ok(data=response, message="프론티어 분석 완료")


@router.get("/history")
async def history(
    ticker: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
):
    usecase = GetFrontierHistoryUseCase(
        analysis_repository_port=FrontierAnalysisRepositoryImpl()
    )
    items = await usecase.execute(ticker=ticker, limit=limit)
    return BaseResponse.ok(
        data={"items": [i.model_dump() for i in items]},
        message="분석 이력 조회 완료",
    )


@router.get("/audit")
async def audit(limit: int = Query(default=50, ge=1, le=200)):
    rows = await FrontierAuditRepositoryImpl().find_recent(limit=limit)
    return BaseResponse.ok(data={"items": rows}, message="감사 로그 조회 완료")
