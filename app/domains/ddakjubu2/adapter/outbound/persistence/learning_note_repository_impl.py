from datetime import date, datetime, time
from typing import Callable, List, Optional, Tuple

from sqlalchemy import exists, func, select

from app.domains.ddakjubu2.application.port.learning_note_repository_port import (
    LearningNoteRepositoryPort,
    LearningNoteSummaryData,
)
from app.domains.ddakjubu2.domain.entity.learning_note import LearningNote
from app.domains.ddakjubu2.infrastructure.mapper.learning_note_mapper import (
    LearningNoteMapper,
)
from app.domains.ddakjubu2.infrastructure.orm.learning_note_orm import LearningNoteOrm
from app.domains.ddakjubu2.infrastructure.orm.methodology_orm import MethodologyOrm
from app.infrastructure.database.database import AsyncSessionLocal


class LearningNoteRepositoryImpl(LearningNoteRepositoryPort):
    """세션 팩토리 기반 구현 — 라우터/BackgroundTasks/APScheduler 어디서든 사용 가능."""

    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def save_note(
        self, note: LearningNote, has_transcript: bool, source: str
    ) -> None:
        async with self._session_factory() as session:
            row = LearningNoteMapper.to_orm(note, has_transcript, source)
            session.add(row)
            await session.commit()

    async def exists(self, video_id: str) -> bool:
        async with self._session_factory() as session:
            stmt = select(
                exists().where(LearningNoteOrm.video_id == video_id)
            )
            result = await session.execute(stmt)
            return bool(result.scalar())

    async def find_notes(
        self,
        limit: int,
        offset: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> Tuple[List[LearningNoteSummaryData], int]:
        async with self._session_factory() as session:
            conditions = []
            if date_from is not None:
                conditions.append(
                    LearningNoteOrm.published_at >= datetime.combine(date_from, time.min)
                )
            if date_to is not None:
                conditions.append(
                    LearningNoteOrm.published_at <= datetime.combine(date_to, time.max)
                )

            count_stmt = select(func.count(LearningNoteOrm.id)).where(*conditions)
            total = (await session.execute(count_stmt)).scalar() or 0

            has_methodology = (
                select(MethodologyOrm.id)
                .where(MethodologyOrm.video_id == LearningNoteOrm.video_id)
                .exists()
            )
            stmt = (
                select(LearningNoteOrm, has_methodology.label("has_methodology"))
                .where(*conditions)
                .order_by(LearningNoteOrm.published_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await session.execute(stmt)

            items: List[LearningNoteSummaryData] = []
            for row, has_method in result.all():
                insights = row.stock_insights or []
                items.append(
                    LearningNoteSummaryData(
                        video_id=row.video_id,
                        video_title=row.video_title,
                        program_category=row.program_category,
                        published_at=row.published_at,
                        summary=row.summary,
                        stock_names=[
                            str(i.get("stock_name", ""))
                            for i in insights
                            if isinstance(i, dict) and i.get("stock_name")
                        ],
                        has_transcript=row.has_transcript,
                        has_methodology=bool(has_method),
                    )
                )
            return items, int(total)

    async def find_by_video_id(self, video_id: str) -> Optional[LearningNote]:
        async with self._session_factory() as session:
            stmt = select(LearningNoteOrm).where(LearningNoteOrm.video_id == video_id)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return LearningNoteMapper.to_entity(row) if row else None

    async def find_video_ids_without_methodology(self, limit: int) -> List[str]:
        async with self._session_factory() as session:
            has_methodology = (
                select(MethodologyOrm.id)
                .where(MethodologyOrm.video_id == LearningNoteOrm.video_id)
                .exists()
            )
            stmt = (
                select(LearningNoteOrm.video_id)
                .where(~has_methodology)
                .order_by(LearningNoteOrm.published_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.all()]
