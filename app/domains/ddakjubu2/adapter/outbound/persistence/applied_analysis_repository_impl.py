from typing import Callable, List, Optional

from sqlalchemy import select

from app.domains.ddakjubu2.application.port.applied_analysis_repository_port import (
    AppliedAnalysisRepositoryPort,
)
from app.domains.ddakjubu2.domain.entity.applied_analysis import AppliedAnalysis
from app.domains.ddakjubu2.infrastructure.mapper.applied_analysis_mapper import (
    AppliedAnalysisMapper,
)
from app.domains.ddakjubu2.infrastructure.orm.applied_analysis_orm import (
    AppliedAnalysisOrm,
)
from app.infrastructure.database.database import AsyncSessionLocal


class AppliedAnalysisRepositoryImpl(AppliedAnalysisRepositoryPort):
    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def save(self, analysis: AppliedAnalysis) -> None:
        async with self._session_factory() as session:
            session.add(AppliedAnalysisMapper.to_orm(analysis))
            await session.commit()

    async def find_history(
        self, ticker: Optional[str], limit: int
    ) -> List[AppliedAnalysis]:
        async with self._session_factory() as session:
            stmt = select(AppliedAnalysisOrm)
            if ticker:
                stmt = stmt.where(AppliedAnalysisOrm.ticker == ticker)
            stmt = stmt.order_by(AppliedAnalysisOrm.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            return [
                AppliedAnalysisMapper.to_entity(row)
                for row in result.scalars().all()
            ]
