from typing import Callable, List, Optional, Tuple

from sqlalchemy import select

from app.domains.fab_agent.application.port.fab_persistence_ports import (
    FabAccessRepositoryPort,
    FabAuditRepositoryPort,
    FabChatRepositoryPort,
    FabFeedbackRepositoryPort,
)
from app.domains.fab_agent.domain.entity.fab_user_access import FabUserAccess
from app.domains.fab_agent.infrastructure.orm.fab_access_orm import FabUserAccessOrm
from app.domains.fab_agent.infrastructure.orm.fab_audit_orm import (
    FabAuditLogOrm,
    FabChatMessageOrm,
    FabFeedbackOrm,
)
from app.infrastructure.database.database import AsyncSessionLocal


class FabAccessRepositoryImpl(FabAccessRepositoryPort):
    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def get_access(self, account_email: str) -> Optional[FabUserAccess]:
        async with self._session_factory() as session:
            stmt = select(FabUserAccessOrm).where(
                FabUserAccessOrm.account_email == account_email.strip().lower()
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                return None
            return FabUserAccess(
                account_email=row.account_email,
                clearance_grade=row.clearance_grade,
                modules=list(row.modules or []),
                is_admin=row.is_admin,
            )

    async def upsert_access(self, access: FabUserAccess) -> None:
        async with self._session_factory() as session:
            stmt = select(FabUserAccessOrm).where(
                FabUserAccessOrm.account_email == access.account_email
            )
            row = (await session.execute(stmt)).scalar_one_or_none()
            if row is None:
                row = FabUserAccessOrm(account_email=access.account_email)
                session.add(row)
            row.clearance_grade = access.clearance_grade
            row.modules = access.modules
            row.is_admin = access.is_admin
            await session.commit()

    async def list_access(self) -> List[FabUserAccess]:
        async with self._session_factory() as session:
            rows = (
                (
                    await session.execute(
                        select(FabUserAccessOrm).order_by(
                            FabUserAccessOrm.account_email
                        )
                    )
                )
                .scalars()
                .all()
            )
            return [
                FabUserAccess(
                    account_email=r.account_email,
                    clearance_grade=r.clearance_grade,
                    modules=list(r.modules or []),
                    is_admin=r.is_admin,
                )
                for r in rows
            ]


class FabAuditRepositoryImpl(FabAuditRepositoryPort):
    """불변 감사 로그 — INSERT/SELECT 만 구현한다 (UPDATE/DELETE 없음)."""

    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def save(
        self,
        request_id: str,
        account_email: str,
        session_id: str,
        question: str,
        answer: str,
        citations: List[dict],
        used_grade_max: int,
        refused: bool,
        latency_ms: int,
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                FabAuditLogOrm(
                    request_id=request_id,
                    account_email=account_email,
                    session_id=session_id,
                    question=question,
                    answer=answer,
                    citations=citations,
                    used_grade_max=used_grade_max,
                    refused=refused,
                    latency_ms=latency_ms,
                )
            )
            await session.commit()

    async def find_recent(
        self, limit: int, account_email: Optional[str] = None
    ) -> List[dict]:
        async with self._session_factory() as session:
            stmt = select(FabAuditLogOrm)
            if account_email:
                stmt = stmt.where(FabAuditLogOrm.account_email == account_email)
            stmt = stmt.order_by(FabAuditLogOrm.created_at.desc()).limit(limit)
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "request_id": r.request_id,
                    "account_email": r.account_email,
                    "session_id": r.session_id,
                    "question": r.question,
                    "answer": r.answer,
                    "used_grade_max": r.used_grade_max,
                    "refused": r.refused,
                    "latency_ms": r.latency_ms,
                    "created_at": r.created_at,
                }
                for r in rows
            ]


class FabChatRepositoryImpl(FabChatRepositoryPort):
    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def recent_messages(
        self, session_id: str, limit: int
    ) -> List[Tuple[str, str]]:
        async with self._session_factory() as session:
            stmt = (
                select(FabChatMessageOrm)
                .where(FabChatMessageOrm.session_id == session_id)
                .order_by(FabChatMessageOrm.id.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [(r.role, r.content) for r in reversed(rows)]

    async def save_message(
        self,
        session_id: str,
        account_email: str,
        role: str,
        content: str,
        citations: Optional[List[dict]] = None,
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                FabChatMessageOrm(
                    session_id=session_id,
                    account_email=account_email,
                    role=role,
                    content=content,
                    citations=citations,
                )
            )
            await session.commit()

    async def session_messages(
        self, session_id: str, account_email: str
    ) -> List[dict]:
        async with self._session_factory() as session:
            stmt = (
                select(FabChatMessageOrm)
                .where(FabChatMessageOrm.session_id == session_id)
                .where(FabChatMessageOrm.account_email == account_email)
                .order_by(FabChatMessageOrm.id.asc())
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [
                {
                    "role": r.role,
                    "content": r.content,
                    "citations": r.citations,
                    "created_at": r.created_at,
                }
                for r in rows
            ]


class FabFeedbackRepositoryImpl(FabFeedbackRepositoryPort):
    def __init__(self, session_factory: Optional[Callable] = None):
        self._session_factory = session_factory or AsyncSessionLocal

    async def save(
        self,
        request_id: str,
        account_email: str,
        rating: str,
        reason: Optional[str],
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                FabFeedbackOrm(
                    request_id=request_id,
                    account_email=account_email,
                    rating=rating,
                    reason=reason,
                )
            )
            await session.commit()
