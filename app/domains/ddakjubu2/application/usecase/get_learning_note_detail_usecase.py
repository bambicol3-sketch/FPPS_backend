from typing import Optional

from app.domains.ddakjubu2.application.port.learning_note_repository_port import (
    LearningNoteRepositoryPort,
)
from app.domains.ddakjubu2.application.port.methodology_repository_port import (
    MethodologyRepositoryPort,
)
from app.domains.ddakjubu2.application.response.learning_note_response import (
    LearningNoteDetailResponse,
    MethodologyDto,
    MethodologyStepDto,
    StockInsightDto,
)
from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology


def methodology_to_dto(methodology: AnalysisMethodology) -> MethodologyDto:
    return MethodologyDto(
        video_id=methodology.video_id,
        video_title=methodology.video_title,
        methodology_name=methodology.methodology_name,
        analysis_steps=[
            MethodologyStepDto(
                step_order=s.step_order,
                name=s.name,
                description=s.description,
                indicators=s.indicators,
                decision_rules=s.decision_rules,
            )
            for s in methodology.analysis_steps
        ],
        indicators_used=methodology.indicators_used,
        decision_rules=methodology.decision_rules,
        risk_management=methodology.risk_management,
        applicable_market_conditions=methodology.applicable_market_conditions,
        example_stocks=[
            {
                "stock_name": e.stock_name,
                "ticker": e.ticker,
                "applied_view": e.applied_view,
            }
            for e in methodology.example_stocks
        ],
        extracted_at=methodology.extracted_at,
    )


class GetLearningNoteDetailUseCase:
    def __init__(
        self,
        note_repository_port: LearningNoteRepositoryPort,
        methodology_repository_port: MethodologyRepositoryPort,
    ):
        self._note_repository_port = note_repository_port
        self._methodology_repository_port = methodology_repository_port

    async def execute(self, video_id: str) -> Optional[LearningNoteDetailResponse]:
        note = await self._note_repository_port.find_by_video_id(video_id)
        if note is None:
            return None

        methodology = await self._methodology_repository_port.find_by_video_id(video_id)

        return LearningNoteDetailResponse(
            video_id=note.video_id,
            video_title=note.video_title,
            channel_name=note.channel_name,
            program_category=note.program_category,
            published_at=note.published_at,
            learned_at=note.learned_at,
            summary=note.summary,
            stock_insights=[
                StockInsightDto(
                    stock_name=i.stock_name,
                    ticker=i.ticker,
                    investment_view=i.investment_view,
                    key_claims=i.key_claims,
                    supporting_evidence=i.supporting_evidence,
                )
                for i in note.stock_insights
            ],
            methodology=methodology_to_dto(methodology) if methodology else None,
        )
