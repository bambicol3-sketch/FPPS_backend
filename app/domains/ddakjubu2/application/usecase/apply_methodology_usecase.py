import re
from typing import List, Optional, Tuple

from app.common.exception.app_exception import AppException
from app.domains.ddakjubu2.application.port.applied_analysis_cache_port import (
    AppliedAnalysisCachePort,
)
from app.domains.ddakjubu2.application.port.applied_analysis_repository_port import (
    AppliedAnalysisRepositoryPort,
)
from app.domains.ddakjubu2.application.port.methodology_apply_port import (
    MethodologyApplyPort,
)
from app.domains.ddakjubu2.application.port.methodology_repository_port import (
    MethodologyRepositoryPort,
)
from app.domains.ddakjubu2.application.port.stock_context_provider_port import (
    StockContextProviderPort,
)
from app.domains.ddakjubu2.application.request.apply_analysis_request import (
    ApplyAnalysisRequest,
)
from app.domains.ddakjubu2.application.response.applied_analysis_response import (
    AppliedAnalysisResponse,
    AppliedStepResultDto,
)
from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology
from app.domains.ddakjubu2.domain.entity.applied_analysis import AppliedAnalysis
from app.domains.stock.application.port.stock_repository import StockRepository

TICKER_PATTERN = re.compile(r"^\d{6}$")
CACHE_KEY_PREFIX = "ddakjubu2:apply:"


def analysis_to_response(
    analysis: AppliedAnalysis, cached: bool = False
) -> AppliedAnalysisResponse:
    return AppliedAnalysisResponse(
        ticker=analysis.ticker,
        stock_name=analysis.stock_name,
        mode=analysis.mode,
        video_id=analysis.video_id,
        master_version=analysis.master_version,
        methodology_name=analysis.methodology_name,
        overall_view=analysis.overall_view,
        confidence=analysis.confidence,
        step_results=[
            AppliedStepResultDto(
                step_order=s.step_order,
                step_name=s.step_name,
                data_used=s.data_used,
                assessment=s.assessment,
                view_contribution=s.view_contribution,
            )
            for s in analysis.step_results
        ],
        missing_data=analysis.missing_data,
        caveats=analysis.caveats,
        summary=analysis.summary,
        analyzed_at=analysis.analyzed_at,
        cached=cached,
    )


class ApplyMethodologyUseCase:
    """딱주부 방법론(특정 방송 또는 종합)을 사용자가 고른 종목에 적용한다."""

    def __init__(
        self,
        stock_repository: StockRepository,
        methodology_repository_port: MethodologyRepositoryPort,
        stock_context_provider_port: StockContextProviderPort,
        methodology_apply_port: MethodologyApplyPort,
        applied_analysis_repository_port: AppliedAnalysisRepositoryPort,
        cache_port: Optional[AppliedAnalysisCachePort] = None,
        cache_ttl_seconds: int = 21600,
    ):
        self._stock_repository = stock_repository
        self._methodology_repository_port = methodology_repository_port
        self._stock_context_provider_port = stock_context_provider_port
        self._methodology_apply_port = methodology_apply_port
        self._applied_analysis_repository_port = applied_analysis_repository_port
        self._cache_port = cache_port
        self._cache_ttl_seconds = cache_ttl_seconds

    async def execute(self, request: ApplyAnalysisRequest) -> AppliedAnalysisResponse:
        ticker, stock_name, market = await self._resolve_stock(request.stock_input)
        methodology, master_version = await self._load_methodology(request)

        cache_key = self._build_cache_key(request, master_version, ticker)
        if self._cache_port is not None:
            cached = await self._cache_port.get(cache_key)
            if cached is not None:
                cached.cached = True
                return cached

        stock_context = await self._stock_context_provider_port.build_context(
            ticker=ticker, stock_name=stock_name, market=market
        )

        analysis = await self._methodology_apply_port.apply(
            methodology=methodology,
            stock_context=stock_context,
            stock_name=stock_name,
            ticker=ticker,
        )
        analysis.mode = request.mode
        analysis.video_id = request.video_id if request.mode == "per_video" else None
        analysis.master_version = master_version

        try:
            await self._applied_analysis_repository_port.save(analysis)
        except Exception as e:
            print(f"[ddakjubu2_apply] 결과 저장 실패 ticker={ticker} error={e}", flush=True)

        response = analysis_to_response(analysis, cached=False)
        if self._cache_port is not None:
            await self._cache_port.save(cache_key, response, self._cache_ttl_seconds)
        return response

    async def _resolve_stock(self, stock_input: str) -> Tuple[str, str, str]:
        query = stock_input.strip()

        if TICKER_PATTERN.match(query):
            stock = await self._stock_repository.find_by_ticker(query)
            if stock is not None:
                return stock.ticker, stock.stock_name, stock.market
            # CSV 에 없어도 6자리 코드는 KRX 조회가 가능하므로 그대로 진행
            return query, query, "KOSPI"

        stock = await self._stock_repository.find_by_company_name(query)
        if stock is not None:
            return stock.ticker, stock.stock_name, stock.market

        raise AppException(
            status_code=404,
            message=(
                f"'{query}' 종목을 찾을 수 없습니다. "
                "6자리 종목 코드(예: 005930)로 다시 시도해 주세요."
            ),
        )

    async def _load_methodology(
        self, request: ApplyAnalysisRequest
    ) -> Tuple[AnalysisMethodology, Optional[int]]:
        if request.mode == "per_video":
            if not request.video_id:
                raise AppException(
                    status_code=400,
                    message="mode=per_video 인 경우 video_id 가 필요합니다.",
                )
            methodology = await self._methodology_repository_port.find_by_video_id(
                request.video_id
            )
            if methodology is None:
                raise AppException(
                    status_code=404,
                    message="해당 방송의 방법론이 아직 추출되지 않았습니다.",
                )
            if methodology.is_empty():
                raise AppException(
                    status_code=409,
                    message=(
                        "이 방송에서는 분석 방법론이 드러나지 않았습니다. "
                        "종합 방법론(master 모드)을 사용해 주세요."
                    ),
                )
            return methodology, None

        master = await self._methodology_repository_port.find_latest_master()
        if master is None:
            raise AppException(
                status_code=409,
                message=(
                    "종합 방법론이 아직 생성되지 않았습니다. "
                    "방법론 추출 및 마스터 재생성을 먼저 실행해 주세요."
                ),
            )
        methodology, version = master
        return methodology, version

    @staticmethod
    def _build_cache_key(
        request: ApplyAnalysisRequest, master_version: Optional[int], ticker: str
    ) -> str:
        if request.mode == "per_video":
            scope = request.video_id or ""
        else:
            scope = f"master-v{master_version or 0}"
        return f"{CACHE_KEY_PREFIX}{request.mode}:{scope}:{ticker}"


class GetAppliedAnalysisHistoryUseCase:
    def __init__(
        self, applied_analysis_repository_port: AppliedAnalysisRepositoryPort
    ):
        self._applied_analysis_repository_port = applied_analysis_repository_port

    async def execute(
        self, ticker: Optional[str], limit: int
    ) -> List[AppliedAnalysisResponse]:
        analyses = await self._applied_analysis_repository_port.find_history(
            ticker=ticker, limit=limit
        )
        return [analysis_to_response(a) for a in analyses]
