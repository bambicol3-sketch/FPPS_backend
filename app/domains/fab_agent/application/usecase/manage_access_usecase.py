from typing import List

from app.common.exception.app_exception import AppException
from app.domains.fab_agent.application.port.fab_persistence_ports import (
    FabAccessRepositoryPort,
    FabAuditRepositoryPort,
    FabChatRepositoryPort,
    FabFeedbackRepositoryPort,
)
from app.domains.fab_agent.application.request.fab_requests import (
    FeedbackRequest,
    UpsertAccessRequest,
)
from app.domains.fab_agent.application.response.fab_responses import (
    FabAccessDto,
    FabAuditEntryDto,
    FabChatMessageDto,
)
from app.domains.fab_agent.domain.entity.fab_document import COMMON_MODULE
from app.domains.fab_agent.domain.entity.fab_user_access import FabUserAccess


def access_to_dto(access: FabUserAccess) -> FabAccessDto:
    return FabAccessDto(
        account_email=access.account_email,
        clearance_grade=access.clearance_grade,
        modules=access.modules,
        is_admin=access.is_admin,
    )


class ManageAccessUseCase:
    def __init__(self, access_repository_port: FabAccessRepositoryPort):
        self._access_repository_port = access_repository_port

    async def upsert(
        self, actor: FabUserAccess, request: UpsertAccessRequest
    ) -> FabAccessDto:
        if not actor.is_admin:
            raise AppException(status_code=403, message="권한 관리는 관리자만 가능합니다.")
        modules = [m.strip().upper() for m in request.modules if m.strip()]
        if COMMON_MODULE not in modules:
            modules.append(COMMON_MODULE)
        if request.is_admin and "*" not in modules:
            modules.append("*")  # 관리자는 전 모듈 열람
        access = FabUserAccess(
            account_email=request.account_email.strip().lower(),
            clearance_grade=request.clearance_grade,
            modules=modules,
            is_admin=request.is_admin,
        )
        await self._access_repository_port.upsert_access(access)
        return access_to_dto(access)

    async def list_all(self, actor: FabUserAccess) -> List[FabAccessDto]:
        if not actor.is_admin:
            raise AppException(status_code=403, message="권한 관리는 관리자만 가능합니다.")
        entries = await self._access_repository_port.list_access()
        return [access_to_dto(a) for a in entries]


class GetAuditLogsUseCase:
    def __init__(self, audit_repository_port: FabAuditRepositoryPort):
        self._audit_repository_port = audit_repository_port

    async def execute(
        self, actor: FabUserAccess, limit: int
    ) -> List[FabAuditEntryDto]:
        if not actor.is_admin:
            raise AppException(status_code=403, message="감사 로그는 관리자만 조회 가능합니다.")
        rows = await self._audit_repository_port.find_recent(limit=limit)
        return [FabAuditEntryDto(**row) for row in rows]


class GetSessionMessagesUseCase:
    def __init__(self, chat_repository_port: FabChatRepositoryPort):
        self._chat_repository_port = chat_repository_port

    async def execute(
        self, account_email: str, session_id: str
    ) -> List[FabChatMessageDto]:
        rows = await self._chat_repository_port.session_messages(
            session_id, account_email
        )
        return [FabChatMessageDto(**row) for row in rows]


class SaveFeedbackUseCase:
    def __init__(self, feedback_repository_port: FabFeedbackRepositoryPort):
        self._feedback_repository_port = feedback_repository_port

    async def execute(self, account_email: str, request: FeedbackRequest) -> None:
        await self._feedback_repository_port.save(
            request_id=request.request_id,
            account_email=account_email,
            rating=request.rating,
            reason=request.reason,
        )
