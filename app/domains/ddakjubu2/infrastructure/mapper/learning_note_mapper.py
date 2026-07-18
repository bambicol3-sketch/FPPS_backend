from datetime import datetime, timezone
from typing import List

from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote, StockInsight
from app.domains.ddakjubu2.infrastructure.orm.learning_note_orm import LearningNoteOrm


def to_naive_utc(value: datetime) -> datetime:
    """tz-aware datetime 을 UTC 기준 naive 로 정규화한다 (DateTime 컬럼은 naive)."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


class LearningNoteMapper:
    @staticmethod
    def insights_to_json(insights: List[StockInsight]) -> List[dict]:
        return [
            {
                "stock_name": i.stock_name,
                "ticker": i.ticker,
                "investment_view": i.investment_view,
                "key_claims": list(i.key_claims),
                "supporting_evidence": list(i.supporting_evidence),
            }
            for i in insights
        ]

    @staticmethod
    def insights_from_json(raw: List[dict]) -> List[StockInsight]:
        insights: List[StockInsight] = []
        for item in raw or []:
            if not isinstance(item, dict):
                continue
            insights.append(
                StockInsight(
                    stock_name=str(item.get("stock_name", "")),
                    ticker=str(item.get("ticker", "")),
                    investment_view=str(item.get("investment_view", "")),
                    key_claims=[str(c) for c in (item.get("key_claims") or [])],
                    supporting_evidence=[
                        str(e) for e in (item.get("supporting_evidence") or [])
                    ],
                )
            )
        return insights

    @classmethod
    def to_orm(
        cls, note: LearningNote, has_transcript: bool, source: str
    ) -> LearningNoteOrm:
        return LearningNoteOrm(
            video_id=note.video_id,
            video_title=note.video_title,
            channel_name=note.channel_name,
            program_category=note.program_category,
            published_at=to_naive_utc(note.published_at),
            learned_at=to_naive_utc(note.learned_at),
            summary=note.summary,
            stock_insights=cls.insights_to_json(note.stock_insights),
            has_transcript=has_transcript,
            source=source,
        )

    @classmethod
    def to_entity(cls, row: LearningNoteOrm) -> LearningNote:
        return LearningNote(
            video_id=row.video_id,
            video_title=row.video_title,
            channel_name=row.channel_name,
            program_category=row.program_category,
            published_at=row.published_at,
            learned_at=row.learned_at,
            summary=row.summary,
            stock_insights=cls.insights_from_json(row.stock_insights),
        )
