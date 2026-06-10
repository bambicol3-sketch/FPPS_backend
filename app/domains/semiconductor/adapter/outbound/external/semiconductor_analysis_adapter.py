from app.domains.semiconductor.application.port.semiconductor_analysis_port import (
    SemiconductorAnalysisPort,
)
from app.domains.semiconductor.domain.entity.semiconductor_analysis import (
    ConversationStep,
    SemiconductorAnalysis,
)
from app.domains.semiconductor.domain.value_object.semiconductor_company import SemiconductorCompany
from app.infrastructure.multi_agent.runner import MultiAgentInput, run_multi_agent

_SEMICONDUCTOR_CONTEXT = (
    "※ 이 분석은 반도체 산업 전문 에이전트가 수행합니다. "
    "한국 반도체 기업(삼성전자·SK하이닉스 등) 및 글로벌 반도체 공급망(TSMC·Intel·NVIDIA·ASML 등) 관점에서 "
    "메모리/파운드리/소재/장비 세그먼트를 고려하여 분석하세요.\n\n"
)


class SemiconductorAnalysisAdapter(SemiconductorAnalysisPort):
    async def analyze(self, ticker: str, query: str) -> SemiconductorAnalysis:
        company = SemiconductorCompany.find_by_ticker(ticker)
        company_name = company.name if company else ticker
        segment = company.segment if company else "반도체"

        enriched_query = _SEMICONDUCTOR_CONTEXT + query

        output = await run_multi_agent(MultiAgentInput(query=enriched_query))

        conversation = [
            ConversationStep(role=msg["role"], node=msg["node"], content=msg["content"])
            for msg in output.messages
        ]

        return SemiconductorAnalysis(
            ticker=ticker,
            company_name=company_name,
            segment=segment,
            query=query,
            final_answer=output.final_answer,
            plan=output.plan,
            research=output.research,
            analysis=output.analysis,
            review=output.review,
            conversation=conversation,
            step_count=output.step_count,
        )
