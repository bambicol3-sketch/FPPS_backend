from app.domains.semiconductor.application.port.semiconductor_analysis_port import (
    SemiconductorAnalysisPort,
)
from app.domains.semiconductor.application.request.semiconductor_analysis_request import (
    SemiconductorAnalysisRequest,
)
from app.domains.semiconductor.domain.entity.semiconductor_analysis import SemiconductorAnalysis
from app.domains.semiconductor.domain.value_object.semiconductor_company import SemiconductorCompany


_DEFAULT_QUERY_TEMPLATE = (
    "{company}({ticker}) 반도체 사업 현황을 분석해 주세요. "
    "주요 제품 경쟁력, 글로벌 시장 내 포지셔닝, 최근 업황 변화 및 투자 관점 리스크와 기회를 포함해 주세요."
)


class AnalyzeSemiconductorUseCase:
    def __init__(self, analysis_port: SemiconductorAnalysisPort) -> None:
        self._port = analysis_port

    async def execute(self, request: SemiconductorAnalysisRequest) -> SemiconductorAnalysis:
        company = SemiconductorCompany.find_by_ticker(request.ticker)
        company_name = company.name if company else request.ticker
        segment = company.segment if company else "반도체"

        query = request.query or _DEFAULT_QUERY_TEMPLATE.format(
            company=company_name, ticker=request.ticker
        )

        return await self._port.analyze(ticker=request.ticker, query=query)
