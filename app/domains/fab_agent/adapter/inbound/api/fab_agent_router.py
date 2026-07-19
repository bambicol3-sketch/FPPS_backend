from fastapi import APIRouter, Depends, Query

from app.common.response.base_response import BaseResponse
from app.domains.fab_agent.adapter.inbound.api.fab_auth import (
    resolve_access,
    resolve_user_email,
)
from app.domains.fab_agent.adapter.outbound.external.openai_compatible_clients import (
    OpenAICompatibleEmbeddingClient,
    OpenAICompatibleLlmClient,
)
from app.domains.fab_agent.adapter.outbound.persistence.fab_document_repository_impl import (
    FabDocumentRepositoryImpl,
)
from app.domains.fab_agent.adapter.outbound.persistence.fab_persistence_impls import (
    FabAccessRepositoryImpl,
    FabAuditRepositoryImpl,
    FabChatRepositoryImpl,
    FabFeedbackRepositoryImpl,
)
from app.domains.fab_agent.application.request.fab_requests import (
    AskRequest,
    FeedbackRequest,
    IngestDocumentRequest,
    UpsertAccessRequest,
)
from app.domains.fab_agent.application.usecase.ask_knowledge_usecase import (
    AskKnowledgeUseCase,
)
from app.domains.fab_agent.application.usecase.manage_access_usecase import (
    GetAuditLogsUseCase,
    GetSessionMessagesUseCase,
    ManageAccessUseCase,
    SaveFeedbackUseCase,
)
from app.domains.fab_agent.application.usecase.manage_documents_usecase import (
    DeleteDocumentUseCase,
    IngestDocumentUseCase,
    ListDocumentsUseCase,
)
from app.infrastructure.config.settings import get_settings

router = APIRouter(prefix="/fab-agent", tags=["fab-agent"])


def _embedding_client(settings) -> OpenAICompatibleEmbeddingClient:
    return OpenAICompatibleEmbeddingClient(
        api_key=settings.fab_llm_api_key or settings.openai_api_key,
        model=settings.fab_embedding_model,
        base_url=settings.fab_embedding_base_url,
    )


@router.post("/ask")
async def ask(request: AskRequest, email: str = Depends(resolve_user_email)):
    settings = get_settings()
    access = await resolve_access(email)
    usecase = AskKnowledgeUseCase(
        document_repository_port=FabDocumentRepositoryImpl(),
        embedding_port=_embedding_client(settings),
        llm_port=OpenAICompatibleLlmClient(
            api_key=settings.fab_llm_api_key or settings.openai_api_key,
            model=settings.fab_llm_model,
            base_url=settings.fab_llm_base_url,
        ),
        audit_repository_port=FabAuditRepositoryImpl(),
        chat_repository_port=FabChatRepositoryImpl(),
        top_k=settings.fab_search_top_k,
        max_history_turns=settings.fab_max_history_turns,
    )
    response = await usecase.execute(access, request.question, request.session_id)
    return BaseResponse.ok(data=response, message="응답 생성 완료")


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str, email: str = Depends(resolve_user_email)
):
    usecase = GetSessionMessagesUseCase(
        chat_repository_port=FabChatRepositoryImpl()
    )
    messages = await usecase.execute(email, session_id)
    return BaseResponse.ok(
        data={"messages": [m.model_dump() for m in messages]},
        message="대화 이력 조회 완료",
    )


@router.post("/feedback")
async def save_feedback(
    request: FeedbackRequest, email: str = Depends(resolve_user_email)
):
    usecase = SaveFeedbackUseCase(
        feedback_repository_port=FabFeedbackRepositoryImpl()
    )
    await usecase.execute(email, request)
    return BaseResponse.ok(data={"saved": True}, message="피드백 저장 완료")


@router.get("/documents")
async def list_documents(email: str = Depends(resolve_user_email)):
    access = await resolve_access(email)
    usecase = ListDocumentsUseCase(
        document_repository_port=FabDocumentRepositoryImpl()
    )
    documents = await usecase.execute(access)
    return BaseResponse.ok(
        data={"items": [d.model_dump() for d in documents]},
        message="문서 목록 조회 완료",
    )


@router.post("/documents")
async def ingest_document(
    request: IngestDocumentRequest, email: str = Depends(resolve_user_email)
):
    settings = get_settings()
    access = await resolve_access(email)
    usecase = IngestDocumentUseCase(
        document_repository_port=FabDocumentRepositoryImpl(),
        embedding_port=_embedding_client(settings),
    )
    response = await usecase.execute(access, request)
    return BaseResponse.ok(data=response, message="문서 인덱싱 완료")


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, email: str = Depends(resolve_user_email)):
    access = await resolve_access(email)
    usecase = DeleteDocumentUseCase(
        document_repository_port=FabDocumentRepositoryImpl()
    )
    await usecase.execute(access, doc_id)
    return BaseResponse.ok(data={"deleted": True}, message="문서 삭제 완료")


@router.get("/access")
async def list_access(email: str = Depends(resolve_user_email)):
    access = await resolve_access(email)
    usecase = ManageAccessUseCase(
        access_repository_port=FabAccessRepositoryImpl()
    )
    entries = await usecase.list_all(access)
    return BaseResponse.ok(
        data={"items": [a.model_dump() for a in entries], "me": access.account_email},
        message="접근 권한 목록 조회 완료",
    )


@router.get("/me")
async def get_my_access(email: str = Depends(resolve_user_email)):
    access = await resolve_access(email)
    return BaseResponse.ok(
        data={
            "account_email": access.account_email,
            "clearance_grade": access.clearance_grade,
            "modules": access.modules,
            "is_admin": access.is_admin,
        },
        message="내 접근 권한 조회 완료",
    )


@router.post("/access")
async def upsert_access(
    request: UpsertAccessRequest, email: str = Depends(resolve_user_email)
):
    access = await resolve_access(email)
    usecase = ManageAccessUseCase(
        access_repository_port=FabAccessRepositoryImpl()
    )
    entry = await usecase.upsert(access, request)
    return BaseResponse.ok(data=entry, message="접근 권한 저장 완료")


@router.get("/audit")
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    email: str = Depends(resolve_user_email),
):
    access = await resolve_access(email)
    usecase = GetAuditLogsUseCase(audit_repository_port=FabAuditRepositoryImpl())
    entries = await usecase.execute(access, limit)
    return BaseResponse.ok(
        data={"items": [e.model_dump() for e in entries]},
        message="감사 로그 조회 완료",
    )
