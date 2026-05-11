import os
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.domains.authentication.adapter.outbound.cache.session_query_cache_impl import (
    SessionQueryCacheImpl,
)
from app.domains.authentication.adapter.outbound.cache.temp_token_query_cache_impl import (
    TempTokenQueryCacheImpl,
)
from app.domains.authentication.adapter.outbound.persistence.account_info_query_impl import (
    AccountInfoQueryImpl,
)
from app.domains.authentication.application.usecase.get_temp_user_info_usecase import (
    GetTempUserInfoUseCase,
)
from app.domains.template_rag.adapter.outbound.external.openai_embedding_client import (
    OpenAIEmbeddingClient,
)
from app.domains.template_rag.adapter.outbound.file.filesystem_file_reader import (
    FilesystemFileReader,
)
from app.domains.template_rag.adapter.outbound.file.pptx_generator_impl import (
    PptxGeneratorImpl,
)
from app.domains.template_rag.adapter.outbound.persistence.template_chunk_repository_impl import (
    TemplateChunkRepositoryImpl,
)
from app.domains.template_rag.application.request.generate_pptx_request import (
    GeneratePptxRequest,
)
from app.domains.template_rag.application.request.ingest_templates_request import (
    IngestTemplatesRequest,
)
from app.domains.template_rag.application.response.generate_pptx_response import (
    GeneratePptxResponse,
)
from app.domains.template_rag.application.response.ingest_templates_response import (
    IngestTemplatesResponse,
)
from app.domains.template_rag.application.usecase.generate_pptx_from_template_usecase import (
    GeneratePptxFromTemplateUseCase,
)
from app.domains.template_rag.application.usecase.ingest_form_templates_usecase import (
    IngestFormTemplatesUseCase,
)
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.database.database import get_db

router = APIRouter(prefix="/template-rag", tags=["template-rag"])

PPTX_OUTPUT_DIR = os.path.abspath(
    os.path.join(os.getcwd(), "generated_pptx")
)


async def require_authenticated_user(
    request: Request,
    authorization: Optional[str] = Header(default=None),
    token_param: Optional[str] = Query(default=None, alias="token"),
    redis: aioredis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    token = token_param or request.cookies.get("temp_token") or request.cookies.get(
        "user_token"
    )
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AppException(status_code=401, message="인증 토큰이 없습니다.")

    user_info = await GetTempUserInfoUseCase(
        temp_token_query_port=TempTokenQueryCacheImpl(redis),
        session_query_port=SessionQueryCacheImpl(redis),
        account_info_query_port=AccountInfoQueryImpl(db),
    ).execute(token=token)

    if not user_info.is_registered:
        raise AppException(
            status_code=401, message="정식 가입된 사용자만 PPT 를 생성할 수 있습니다."
        )
    return user_info


@router.post("/ingest", response_model=IngestTemplatesResponse)
async def ingest_templates(
    request: IngestTemplatesRequest,
    db: AsyncSession = Depends(get_db),
):
    """B-1: 양식 폴더 → RAG 임베딩 ingest."""
    try:
        usecase = IngestFormTemplatesUseCase(
            repository=TemplateChunkRepositoryImpl(db),
            embedding=OpenAIEmbeddingClient(),
            file_reader=FilesystemFileReader(),
        )
        return await usecase.execute(request)
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/generate-pptx", response_model=GeneratePptxResponse)
async def generate_pptx(
    request: GeneratePptxRequest,
    _user=Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """B-2: 인증된 사용자가 양식 sheet + raw data 폴더로 PPT 생성."""
    try:
        usecase = GeneratePptxFromTemplateUseCase(
            repository=TemplateChunkRepositoryImpl(db),
            embedding=OpenAIEmbeddingClient(),
            file_reader=FilesystemFileReader(),
            pptx_generator=PptxGeneratorImpl(),
            output_dir=PPTX_OUTPUT_DIR,
        )
        return await usecase.execute(request)
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.get("/download/{file_name}")
async def download_pptx(
    file_name: str,
    _user=Depends(require_authenticated_user),
):
    """생성된 PPT 다운로드 (인증 필요)."""
    safe = os.path.basename(file_name)
    file_path = os.path.join(PPTX_OUTPUT_DIR, safe)
    if not os.path.isfile(file_path):
        raise AppException(
            status_code=404, message=f"파일이 존재하지 않습니다: {file_name}"
        )
    return FileResponse(
        file_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        filename=safe,
    )
