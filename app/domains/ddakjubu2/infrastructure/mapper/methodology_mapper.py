from datetime import datetime
from typing import Optional

from app.domains.ddakjubu2.domain.entity.analysis_methodology import (
    AnalysisMethodology,
    MethodologyExample,
    MethodologyStep,
)
from app.domains.ddakjubu2.infrastructure.mapper.learning_note_mapper import to_naive_utc
from app.domains.ddakjubu2.infrastructure.orm.master_methodology_orm import (
    MasterMethodologyOrm,
)
from app.domains.ddakjubu2.infrastructure.orm.methodology_orm import MethodologyOrm


class MethodologyMapper:
    @staticmethod
    def to_json(methodology: AnalysisMethodology) -> dict:
        return {
            "methodology_name": methodology.methodology_name,
            "analysis_steps": [
                {
                    "step_order": s.step_order,
                    "name": s.name,
                    "description": s.description,
                    "indicators": list(s.indicators),
                    "decision_rules": list(s.decision_rules),
                }
                for s in methodology.analysis_steps
            ],
            "indicators_used": list(methodology.indicators_used),
            "decision_rules": list(methodology.decision_rules),
            "risk_management": list(methodology.risk_management),
            "applicable_market_conditions": methodology.applicable_market_conditions,
            "example_stocks": [
                {
                    "stock_name": e.stock_name,
                    "ticker": e.ticker,
                    "applied_view": e.applied_view,
                }
                for e in methodology.example_stocks
            ],
        }

    @staticmethod
    def from_json(
        raw: dict,
        video_id: str,
        video_title: str,
        extracted_at: Optional[datetime] = None,
    ) -> AnalysisMethodology:
        raw = raw or {}
        steps = []
        for item in raw.get("analysis_steps") or []:
            if not isinstance(item, dict):
                continue
            steps.append(
                MethodologyStep(
                    step_order=int(item.get("step_order") or (len(steps) + 1)),
                    name=str(item.get("name", "")),
                    description=str(item.get("description", "")),
                    indicators=[str(i) for i in (item.get("indicators") or [])],
                    decision_rules=[
                        str(r) for r in (item.get("decision_rules") or [])
                    ],
                )
            )
        examples = []
        for item in raw.get("example_stocks") or []:
            if not isinstance(item, dict):
                continue
            examples.append(
                MethodologyExample(
                    stock_name=str(item.get("stock_name", "")),
                    ticker=str(item.get("ticker", "")),
                    applied_view=str(item.get("applied_view", "")),
                )
            )
        return AnalysisMethodology(
            video_id=video_id,
            video_title=video_title,
            methodology_name=str(raw.get("methodology_name", "")),
            analysis_steps=steps,
            indicators_used=[str(i) for i in (raw.get("indicators_used") or [])],
            decision_rules=[str(r) for r in (raw.get("decision_rules") or [])],
            risk_management=[str(r) for r in (raw.get("risk_management") or [])],
            applicable_market_conditions=str(
                raw.get("applicable_market_conditions", "")
            ),
            example_stocks=examples,
            extracted_at=extracted_at or datetime.now(),
        )

    @classmethod
    def to_orm(cls, methodology: AnalysisMethodology, model: str) -> MethodologyOrm:
        return MethodologyOrm(
            video_id=methodology.video_id,
            video_title=methodology.video_title,
            methodology=cls.to_json(methodology),
            extracted_at=to_naive_utc(methodology.extracted_at),
            model=model,
        )

    @classmethod
    def to_entity(cls, row: MethodologyOrm) -> AnalysisMethodology:
        return cls.from_json(
            row.methodology,
            video_id=row.video_id,
            video_title=row.video_title,
            extracted_at=row.extracted_at,
        )

    @classmethod
    def master_to_orm(
        cls,
        methodology: AnalysisMethodology,
        version: int,
        source_video_count: int,
    ) -> MasterMethodologyOrm:
        return MasterMethodologyOrm(
            version=version,
            methodology=cls.to_json(methodology),
            source_video_count=source_video_count,
        )

    @classmethod
    def master_to_entity(cls, row: MasterMethodologyOrm) -> AnalysisMethodology:
        return cls.from_json(
            row.methodology,
            video_id="",
            video_title="딱주부 종합 방법론",
            extracted_at=row.created_at,
        )
