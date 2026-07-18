from datetime import datetime
from typing import Optional

from app.domains.ddakjubu2.domain.entity.applied_analysis import (
    AppliedAnalysis,
    AppliedStepResult,
)
from app.domains.ddakjubu2.infrastructure.mapper.learning_note_mapper import to_naive_utc
from app.domains.ddakjubu2.infrastructure.orm.applied_analysis_orm import (
    AppliedAnalysisOrm,
)


class AppliedAnalysisMapper:
    @staticmethod
    def to_json(analysis: AppliedAnalysis) -> dict:
        return {
            "methodology_name": analysis.methodology_name,
            "master_version": analysis.master_version,
            "step_results": [
                {
                    "step_order": s.step_order,
                    "step_name": s.step_name,
                    "data_used": s.data_used,
                    "assessment": s.assessment,
                    "view_contribution": s.view_contribution,
                }
                for s in analysis.step_results
            ],
            "missing_data": list(analysis.missing_data),
            "caveats": list(analysis.caveats),
            "summary": analysis.summary,
            "analyzed_at": analysis.analyzed_at.isoformat(),
        }

    @staticmethod
    def from_json(
        raw: dict,
        ticker: str,
        stock_name: str,
        mode: str,
        video_id: Optional[str],
        overall_view: str,
        confidence: int,
    ) -> AppliedAnalysis:
        raw = raw or {}
        steps = []
        for item in raw.get("step_results") or []:
            if not isinstance(item, dict):
                continue
            steps.append(
                AppliedStepResult(
                    step_order=int(item.get("step_order") or (len(steps) + 1)),
                    step_name=str(item.get("step_name", "")),
                    data_used=str(item.get("data_used", "")),
                    assessment=str(item.get("assessment", "")),
                    view_contribution=str(item.get("view_contribution", "")),
                )
            )
        analyzed_at_raw = raw.get("analyzed_at", "")
        try:
            analyzed_at = datetime.fromisoformat(analyzed_at_raw)
        except (TypeError, ValueError):
            analyzed_at = datetime.now()
        return AppliedAnalysis(
            ticker=ticker,
            stock_name=stock_name,
            mode=mode,
            video_id=video_id,
            methodology_name=str(raw.get("methodology_name", "")),
            overall_view=overall_view,
            confidence=confidence,
            step_results=steps,
            missing_data=[str(m) for m in (raw.get("missing_data") or [])],
            caveats=[str(c) for c in (raw.get("caveats") or [])],
            summary=str(raw.get("summary", "")),
            analyzed_at=analyzed_at,
            master_version=raw.get("master_version"),
        )

    @classmethod
    def to_orm(cls, analysis: AppliedAnalysis) -> AppliedAnalysisOrm:
        return AppliedAnalysisOrm(
            ticker=analysis.ticker,
            stock_name=analysis.stock_name,
            mode=analysis.mode,
            video_id=analysis.video_id,
            overall_view=analysis.overall_view,
            confidence=analysis.confidence,
            result=cls.to_json(analysis),
        )

    @classmethod
    def to_entity(cls, row: AppliedAnalysisOrm) -> AppliedAnalysis:
        analysis = cls.from_json(
            row.result,
            ticker=row.ticker,
            stock_name=row.stock_name,
            mode=row.mode,
            video_id=row.video_id,
            overall_view=row.overall_view,
            confidence=row.confidence,
        )
        analysis.analyzed_at = to_naive_utc(analysis.analyzed_at)
        return analysis
