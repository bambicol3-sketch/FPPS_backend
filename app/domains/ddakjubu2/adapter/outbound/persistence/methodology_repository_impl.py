from typing import Callable, List, Optional, Tuple

from sqlalchemy import exists, func, select

from app.domains.ddakjubu2.application.port.methodology_repository_port import (
    MethodologyRepositoryPort,
)
from app.domains.ddakjubu2.domain.entity.analysis_methodology import AnalysisMethodology
from app.domains.ddakjubu2.infrastructure.mapper.methodology_mapper import (
    MethodologyMapper,
)
from app.domains.ddakjubu2.infrastructure.orm.master_methodology_orm import (
    MasterMethodologyOrm,
)
from app.domains.ddakjubu2.infrastructure.orm.methodology_orm import MethodologyOrm
from app.infrastructure.database.database import AsyncSessionLocal


class MethodologyRepositoryImpl(MethodologyRepositoryPort):
    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def save(self, methodology: AnalysisMethodology, model: str) -> None:
        async with self._session_factory() as session:
            session.add(MethodologyMapper.to_orm(methodology, model))
            await session.commit()

    async def exists(self, video_id: str) -> bool:
        async with self._session_factory() as session:
            stmt = select(exists().where(MethodologyOrm.video_id == video_id))
            result = await session.execute(stmt)
            return bool(result.scalar())

    async def find_by_video_id(self, video_id: str) -> Optional[AnalysisMethodology]:
        async with self._session_factory() as session:
            stmt = select(MethodologyOrm).where(MethodologyOrm.video_id == video_id)
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return MethodologyMapper.to_entity(row) if row else None

    async def find_recent(self, limit: int) -> List[AnalysisMethodology]:
        async with self._session_factory() as session:
            stmt = (
                select(MethodologyOrm)
                .order_by(MethodologyOrm.extracted_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [MethodologyMapper.to_entity(row) for row in result.scalars().all()]

    async def save_master(
        self, methodology: AnalysisMethodology, source_video_count: int
    ) -> int:
        async with self._session_factory() as session:
            max_version = (
                await session.execute(select(func.max(MasterMethodologyOrm.version)))
            ).scalar() or 0
            next_version = int(max_version) + 1
            session.add(
                MethodologyMapper.master_to_orm(
                    methodology, next_version, source_video_count
                )
            )
            await session.commit()
            return next_version

    async def find_latest_master(
        self,
    ) -> Optional[Tuple[AnalysisMethodology, int]]:
        async with self._session_factory() as session:
            stmt = (
                select(MasterMethodologyOrm)
                .order_by(MasterMethodologyOrm.version.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return MethodologyMapper.master_to_entity(row), row.version
