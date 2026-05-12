import os
from pathlib import Path
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Body, Depends, Header, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
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
from app.domains.template_rag.adapter.outbound.external.openai_llm_json_client import (
    OpenAILlmJsonClient,
)
from app.domains.template_rag.adapter.outbound.file.filesystem_file_reader import (
    SUPPORTED_EXTENSIONS,
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
from app.domains.template_rag.application.response.folder_listing_response import (
    FolderEntry,
    FolderListingResponse,
)
from app.domains.template_rag.application.response.folder_search_response import (
    FolderSearchResponse,
)
from app.domains.template_rag.application.response.ingest_templates_response import (
    IngestTemplatesResponse,
)
from app.domains.template_rag.application.request.validate_folder_request import (
    ValidateFolderRequest,
)
from app.domains.template_rag.application.response.validate_folder_response import (
    ValidateFolderResponse,
)
from app.domains.template_rag.application.request.create_rag_job_request import (
    CreateRagJobRequest,
)
from app.domains.template_rag.application.response.create_rag_job_response import (
    CreateRagJobResponse,
)
from app.domains.template_rag.application.response.identify_template_response import (
    IdentifyTemplateResponse,
)
from app.domains.template_rag.application.config.form_type_mapping import (
    FormTypeMapping,
)
from app.domains.template_rag.domain.value_object.form_type import FormType
from datetime import datetime as _dt
from app.domains.template_rag.application.usecase.generate_pptx_from_template_usecase import (
    GeneratePptxFromTemplateUseCase,
)
from app.domains.template_rag.application.usecase.ingest_form_templates_usecase import (
    IngestFormTemplatesUseCase,
)
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.database.database import get_db

router = APIRouter(tags=["rag"])  # prefix 는 v1_router 에서 mount 시 지정 (/rag, /template-rag 양쪽 지원)

PPTX_OUTPUT_DIR = os.path.abspath(
    os.path.join(os.getcwd(), "generated_pptx")
)

# 동기로 실행되는 /jobs 결과를 프론트가 폴링/스트리밍으로 받아갈 수 있게
# job_id → response payload 를 in-memory 로 캐싱한다. 서버 재시작 시 휘발됨.
_JOBS_CACHE: dict[str, dict] = {}


_STATUS_TO_CODE = {
    "completed": "SUCCESS",
    "partial": "PARTIAL",
    "failed": "FAILED",
    "pending": "PENDING",
    "running": "RUNNING",
}
_STATUS_TO_GEN_CODE = {
    "completed": "GENERATION_SUCCESS",
    "partial": "GENERATION_PARTIAL",
    "failed": "GENERATION_FAILED",
    "pending": "GENERATION_PENDING",
    "running": "GENERATION_RUNNING",
}


def _enrich_status_fields(flat: dict, is_ppt: bool = False) -> dict:
    """프론트의 다양한 status / code / done / progress 필드 명을 모두 채워넣는다."""
    status = flat.get("status", "completed")
    code = _STATUS_TO_CODE.get(status, status.upper() if isinstance(status, str) else "UNKNOWN")
    gen_code = _STATUS_TO_GEN_CODE.get(status, code)
    done = status in ("completed", "partial", "failed")
    progress = 100 if done else 0
    extras = {
        "code": gen_code if is_ppt else code,
        "result_code": gen_code if is_ppt else code,
        "response_code": gen_code if is_ppt else code,
        "statusCode": gen_code if is_ppt else code,
        "generation_code": gen_code,
        "state": status,
        "progress": progress,
        "percent": progress,
        "percentage": progress,
        "done": done,
        "is_done": done,
        "isDone": done,
        "finished": done,
        "completed": status == "completed",
        "error": status == "failed",
        "ok": status == "completed",
    }
    return {**flat, **extras}


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
    """B-1: 양식 폴더 → RAG 임베딩 ingest (양식 PPTX 는 LLM 으로 파싱도 수행)."""
    try:
        usecase = IngestFormTemplatesUseCase(
            repository=TemplateChunkRepositoryImpl(db),
            embedding=OpenAIEmbeddingClient(),
            file_reader=FilesystemFileReader(),
            llm_json=OpenAILlmJsonClient(),
        )
        return await usecase.execute(request)
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.post("/generate-pptx")
async def generate_pptx(
    request: GeneratePptxRequest,
    _user=Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
):
    """B-2: 인증된 사용자가 양식 sheet + raw data 폴더로 PPT 생성.

    응답은 /ppt/jobs 와 동일한 enriched + dual exposure 포맷.
    """
    try:
        usecase = GeneratePptxFromTemplateUseCase(
            repository=TemplateChunkRepositoryImpl(db),
            embedding=OpenAIEmbeddingClient(),
            file_reader=FilesystemFileReader(),
            pptx_generator=PptxGeneratorImpl(),
            output_dir=PPTX_OUTPUT_DIR,
            llm_json=OpenAILlmJsonClient(),
        )
        result = await usecase.execute(request)
    except ValueError as e:
        flat = _enrich_status_fields(
            {
                "status": "failed",
                "form_type": request.form_type,
                "template": request.form_type,
                "folder": request.raw_data_dir,
                "folder_path": request.raw_data_dir,
                "raw_data_folder": request.raw_data_dir,
                "message": f"PPT 생성 실패: {e}",
            },
            is_ppt=True,
        )
        return {**flat, "success": False, "data": flat}
    except Exception as e:
        flat = _enrich_status_fields(
            {
                "status": "failed",
                "form_type": request.form_type,
                "template": request.form_type,
                "folder": request.raw_data_dir,
                "folder_path": request.raw_data_dir,
                "raw_data_folder": request.raw_data_dir,
                "message": f"PPT 생성 중 예외: {e}",
            },
            is_ppt=True,
        )
        return {**flat, "success": False, "data": flat}

    flat = _enrich_status_fields(
        {
            "status": "completed",
            "form_type": result.form_type,
            "template": result.form_type,
            "sheet": result.sheet_name,
            "sheet_name": result.sheet_name,
            "folder": request.raw_data_dir,
            "folder_path": request.raw_data_dir,
            "raw_data_folder": request.raw_data_dir,
            "file_path": result.file_path,
            "file_name": result.file_name,
            "saved_directory": result.saved_directory,
            "download_url": result.download_url,
            "url": result.download_url,
            "pptUrl": result.download_url,
            "ppt_url": result.download_url,
            "downloadUrl": result.download_url,
            "slide_count": result.slide_count,
            "slideCount": result.slide_count,
            "files_read": result.files_read,
            "chunks_referenced": result.chunks_referenced,
            "message": (
                f"PPT 생성 완료: {result.file_name} "
                f"(슬라이드 {result.slide_count}장)"
            ),
        },
        is_ppt=True,
    )
    return {**flat, "success": True, "data": flat}


@router.get("/download/{file_name}")
async def download_pptx(file_name: str):
    """생성된 PPT 다운로드.

    인증을 요구하지 않는다 (파일명에 timestamp 가 들어가 추측이 어렵고,
    프론트가 새 탭/window 로 link 를 열 때 cookie/header 전달이 불안정해
    401 이 잦았던 이슈를 해소).
    """
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


@router.get("/folders", response_model=BaseResponse[FolderListingResponse])
async def list_folders(
    path: Optional[str] = Query(default=None, description="조회할 절대 경로"),
    _user=Depends(require_authenticated_user),
):
    """사용자가 입력한 절대 경로의 디렉토리 항목을 반환한다.

    - 내부 사용 전용: 경로 jail 없음. 사용자가 지정한 절대 경로를 그대로 사용.
    - path 미지정 시 사용자의 홈 디렉토리를 기본으로 사용.
    """
    target = Path(path).expanduser() if path else Path.home()

    try:
        target = target.resolve()
    except OSError as e:
        raise AppException(status_code=400, message=f"경로 해석 실패: {e}")

    if not target.exists():
        raise AppException(status_code=404, message=f"폴더를 찾을 수 없습니다: {target}")
    if not target.is_dir():
        raise AppException(status_code=400, message=f"디렉토리가 아닙니다: {target}")

    entries: list[FolderEntry] = []
    try:
        for child in sorted(
            target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
        ):
            if child.name.startswith("."):
                continue
            try:
                is_dir = child.is_dir()
            except OSError:
                continue
            entries.append(
                FolderEntry(
                    name=child.name,
                    is_directory=is_dir,
                    full_path=str(child),
                )
            )
    except PermissionError:
        raise AppException(status_code=403, message="폴더 접근 권한이 없습니다.")
    except OSError as e:
        raise AppException(status_code=500, message=f"폴더 조회 실패: {e}")

    parent = str(target.parent) if target != target.parent else None

    return BaseResponse.ok(
        data=FolderListingResponse(
            path=str(target),
            parent=parent,
            entries=entries,
        )
    )


@router.get("/folders/search", response_model=BaseResponse[FolderSearchResponse])
async def search_folders(
    name: str = Query(..., min_length=1, description="찾을 폴더 이름"),
    base: Optional[str] = Query(
        default=None,
        description="검색 시작 경로 (기본: 사용자 홈)",
    ),
    max_depth: int = Query(default=6, ge=1, le=10),
    max_matches: int = Query(default=20, ge=1, le=100),
    _user=Depends(require_authenticated_user),
):
    """드래그앤드롭이 폴더 이름만 줄 때, 서버에서 같은 이름의 디렉토리 절대 경로를 찾는다.

    - 기본 시작 경로: 사용자 홈
    - 깊이/매치 수 상한으로 비용 제한
    - 매치 0개면 빈 배열 반환, 단일 매치면 프론트가 그대로 절대 경로로 사용
    """
    root = (Path(base).expanduser() if base else Path.home()).resolve()
    if not root.is_dir():
        raise AppException(status_code=400, message=f"검색 시작 경로가 디렉토리가 아닙니다: {root}")

    matches: list[str] = []
    truncated = False

    def _walk(dir_path: Path, depth: int) -> None:
        nonlocal truncated
        if depth > max_depth or len(matches) >= max_matches:
            return
        try:
            for child in dir_path.iterdir():
                if child.name.startswith("."):
                    continue
                try:
                    if not child.is_dir():
                        continue
                except OSError:
                    continue
                if child.name == name:
                    matches.append(str(child))
                    if len(matches) >= max_matches:
                        truncated = True
                        return
                _walk(child, depth + 1)
        except (OSError, PermissionError):
            return

    _walk(root, 0)

    return BaseResponse.ok(
        data=FolderSearchResponse(
            name=name,
            base=str(root),
            matches=matches,
            truncated=truncated,
        )
    )


@router.post(
    "/folder/validate", response_model=BaseResponse[ValidateFolderResponse]
)
@router.post(
    "/raw-data/validate", response_model=BaseResponse[ValidateFolderResponse]
)
async def validate_folder(
    request: ValidateFolderRequest,
    path_query: Optional[str] = Query(default=None, alias="path"),
    _user=Depends(require_authenticated_user),
):
    """폴더(템플릿 또는 PPT raw data) 검증용 호출.

    - exists/is_directory 확인
    - 지원 확장자(txt/md/pdf/docx/pptx) 파일 개수 + 확장자별 분포 반환
    - body 의 path/folder_path/folderPath/folder/dir 중 하나, 또는 ?path= query 로 전달 가능
    """
    raw_path = request.path or path_query
    if not raw_path:
        raise AppException(
            status_code=400,
            message="path 가 비어 있습니다. body 의 path 필드 또는 ?path= 쿼리로 폴더 경로를 보내주세요.",
        )

    target = Path(raw_path).expanduser()
    try:
        target = target.resolve()
    except OSError as e:
        raise AppException(status_code=400, message=f"경로 해석 실패: {e}")

    if not target.exists():
        return BaseResponse.ok(
            data=ValidateFolderResponse(
                path=str(target),
                exists=False,
                is_directory=False,
                supported_file_count=0,
                total_file_count=0,
                extensions_breakdown={},
                message="폴더가 존재하지 않습니다.",
            )
        )

    if not target.is_dir():
        return BaseResponse.ok(
            data=ValidateFolderResponse(
                path=str(target),
                exists=True,
                is_directory=False,
                supported_file_count=0,
                total_file_count=0,
                extensions_breakdown={},
                message="디렉토리가 아닙니다.",
            )
        )

    supported_count = 0
    total_count = 0
    breakdown: dict[str, int] = {}

    try:
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            if path.name.startswith("."):
                continue
            total_count += 1
            ext = path.suffix.lower()
            if ext in SUPPORTED_EXTENSIONS:
                supported_count += 1
                breakdown[ext] = breakdown.get(ext, 0) + 1
    except PermissionError:
        raise AppException(status_code=403, message="폴더 접근 권한이 없습니다.")
    except OSError as e:
        raise AppException(status_code=500, message=f"폴더 스캔 실패: {e}")

    if supported_count == 0:
        message = (
            "지원 확장자 파일(txt/md/pdf/docx/pptx)이 없습니다."
            if total_count > 0
            else "폴더가 비어 있습니다."
        )
    else:
        message = f"지원 파일 {supported_count}개가 발견되었습니다."

    return BaseResponse.ok(
        data=ValidateFolderResponse(
            path=str(target),
            exists=True,
            is_directory=True,
            supported_file_count=supported_count,
            total_file_count=total_count,
            extensions_breakdown=breakdown,
            message=message,
        )
    )


def _pick(body: dict, keys: list[str]) -> Optional[str]:
    for k in keys:
        v = body.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


@router.post("/jobs")
async def create_rag_job(
    request: Request,
    body: dict = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db),
):
    # /ppt/jobs 로 들어오면 PPT 생성, 그 외(/rag/jobs, /template-rag/jobs)는 RAG ingest
    if "/ppt/" in request.url.path:
        return await _create_ppt_generation_job(body, db)
    """양식 + 폴더 + 시트 단위로 RAG ingest 작업 실행 (동기 처리).

    프론트가 보내는 JSON 키 이름이 다양해 raw dict 로 받아 유연하게 매핑한다.
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)
    _log.info("[/jobs] received keys=%s", list(body.keys()) if isinstance(body, dict) else type(body).__name__)

    # 중첩 케이스 (예: {"job": {...}} / {"data": {...}}) 흡수
    if isinstance(body, dict):
        for wrapper in ("job", "data", "payload", "request"):
            inner = body.get(wrapper)
            if isinstance(inner, dict):
                body = inner
                break

    form_type_raw = _pick(
        body,
        [
            "form_type", "formType", "form", "type",
            "template", "template_type", "templateType",
            "양식", "formName",
        ],
    )
    folder_raw = _pick(
        body,
        [
            "folder", "folder_path", "folderPath", "path", "폴더",
            "folderName", "dir", "directory",
        ],
    )
    sheet_raw = _pick(body, ["sheet", "sheet_name", "sheetName", "시트"])

    if not form_type_raw:
        raise AppException(
            status_code=400,
            message=(
                f"form_type 이 비어 있습니다. 받은 키: {list(body.keys())}. "
                f"지원 키: form_type / formType / form / 양식"
            ),
        )
    if not folder_raw:
        raise AppException(
            status_code=400,
            message=(
                f"folder 가 비어 있습니다. 받은 키: {list(body.keys())}. "
                f"지원 키: folder / folder_path / folderPath / path / 폴더"
            ),
        )

    try:
        form_type = FormType.from_string(form_type_raw)
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))

    sheet_name = sheet_raw or form_type.value
    job_id = f"{form_type.value}_{int(_dt.now().timestamp())}"

    mapping = FormTypeMapping()
    mapping.register(form_type, folder_path=folder_raw, sheet_name=sheet_name)

    usecase = IngestFormTemplatesUseCase(
        repository=TemplateChunkRepositoryImpl(db),
        embedding=OpenAIEmbeddingClient(),
        file_reader=FilesystemFileReader(),
        mapping=mapping,
        llm_json=OpenAILlmJsonClient(),
    )

    try:
        result = await usecase.execute(IngestTemplatesRequest())
    except Exception as e:
        flat = _enrich_status_fields({
            "job_id": job_id,
            "status": "failed",
            "form_type": form_type.value,
            "template": form_type.value,
            "folder": folder_raw,
            "folder_path": folder_raw,
            "sheet": sheet_name,
            "sheet_name": sheet_name,
            "files_processed": 0,
            "files_failed": [],
            "chunks_created": 0,
            "message": f"RAG 처리 중 예외가 발생했습니다: {e}",
        })
        body_out = {**flat, "success": False, "data": flat}
        _JOBS_CACHE[job_id] = body_out
        return body_out

    sheet_result = result.sheets[0]

    if sheet_result.files_processed == 0 and not sheet_result.files_failed:
        status = "failed"
        message = (
            f"폴더에서 처리 가능한 파일을 찾지 못했습니다: {folder_raw}"
        )
    elif sheet_result.files_failed:
        status = "partial"
        message = (
            f"{sheet_result.files_processed}개 파일 처리, "
            f"{len(sheet_result.files_failed)}개 실패, "
            f"{sheet_result.chunks_created}개 청크 생성"
        )
    else:
        status = "completed"
        message = (
            f"{sheet_result.files_processed}개 파일 처리 완료, "
            f"{sheet_result.chunks_created}개 청크 생성"
        )

    flat = _enrich_status_fields({
        "job_id": job_id,
        "status": status,
        "form_type": form_type.value,
        "template": form_type.value,
        "folder": sheet_result.folder_path,
        "folder_path": sheet_result.folder_path,
        "sheet": sheet_result.sheet_name,
        "sheet_name": sheet_result.sheet_name,
        "files_processed": sheet_result.files_processed,
        "files_failed": sheet_result.files_failed,
        "chunks_created": sheet_result.chunks_created,
        "message": message,
    })
    body_out = {**flat, "success": True, "data": flat}
    _JOBS_CACHE[job_id] = body_out
    import logging as _l
    _l.getLogger(__name__).info("[/jobs] response status=%s code=%s done=%s job_id=%s",
                                flat["status"], flat["code"], flat["done"], job_id)
    return body_out


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """동기로 실행된 /jobs 의 결과를 캐시에서 반환."""
    cached = _JOBS_CACHE.get(job_id)
    if not cached:
        raise AppException(
            status_code=404,
            message=f"job '{job_id}' 를 찾을 수 없습니다. (서버 재시작 시 캐시가 비워질 수 있습니다)",
        )
    import logging as _l
    _l.getLogger(__name__).info(
        "[/jobs/%s] keys=%s status=%s code=%s done=%s success=%s",
        job_id, list(cached.keys())[:15],
        cached.get("status"), cached.get("code"),
        cached.get("done"), cached.get("success"),
    )
    return cached


@router.get("/jobs/{job_id}/stream")
async def stream_job_status(job_id: str):
    """SSE 로 job 결과를 1회 전송 후 done 이벤트 후 종료."""
    import json as _json
    from fastapi.responses import StreamingResponse as _StreamingResponse

    cached = _JOBS_CACHE.get(job_id)

    async def event_gen():
        if cached:
            msg = _json.dumps(cached, ensure_ascii=False)
            # 프론트가 어떤 event 타입을 listen 하는지 모르므로 흔한 타입을 모두 broadcast
            for evt in (
                "message", "status", "progress", "update",
                "result", "complete", "completed", "done",
            ):
                yield f"event: {evt}\ndata: {msg}\n\n"
        else:
            payload = _json.dumps(
                {"status": "pending", "job_id": job_id, "message": "처리 중입니다."},
                ensure_ascii=False,
            )
            yield f"event: progress\ndata: {payload}\n\n"
            yield f"data: {payload}\n\n"

    return _StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/templates/identify")
async def identify_template(
    body: dict = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db),
):
    """PPT 생성 prepare 단계.

    프론트가 양식 + raw data 폴더를 보내 'PPT 생성이 가능한가?'를 확인할 때 호출.
    - 해당 양식 sheet 에 청크가 있는지 확인
    - raw data 폴더가 존재/디렉토리/지원 파일을 가졌는지 확인
    - 두 조건 모두 만족하면 ready=True
    """
    import logging as _logging
    _logging.getLogger(__name__).info(
        "[/templates/identify] keys=%s",
        list(body.keys()) if isinstance(body, dict) else type(body).__name__,
    )

    if isinstance(body, dict):
        for wrapper in ("job", "data", "payload", "request"):
            inner = body.get(wrapper)
            if isinstance(inner, dict):
                body = inner
                break

    form_type_raw = _pick(
        body,
        [
            "form_type", "formType", "form", "type",
            "template", "template_type", "templateType",
            "양식", "formName",
        ],
    )
    folder_raw = _pick(
        body,
        [
            "folder", "folder_path", "folderPath", "path",
            "raw_data_folder", "rawDataFolder", "raw_data", "rawData",
            "raw_data_path", "rawDataPath",
            "폴더", "folderName", "dir", "directory",
        ],
    )

    if not form_type_raw and not folder_raw:
        raise AppException(
            status_code=400,
            message=(
                f"form_type 또는 folder 중 하나는 필요합니다. 받은 키: "
                f"{list(body.keys()) if isinstance(body, dict) else []}"
            ),
        )

    # form_type 은 선택. 없으면 raw data 폴더만 검증.
    form_type: Optional[FormType] = None
    if form_type_raw:
        try:
            form_type = FormType.from_string(form_type_raw)
        except ValueError as e:
            raise AppException(status_code=400, message=str(e))

    template_exists = True
    chunk_count = 0
    if form_type is not None:
        repo = TemplateChunkRepositoryImpl(db)
        chunk_count = await repo.count_by_form_type(form_type.value)
        template_exists = chunk_count > 0

    raw_supported_count: Optional[int] = None
    raw_data_ok = True
    raw_message = ""

    if folder_raw:
        from pathlib import Path as _Path

        target = _Path(folder_raw).expanduser()
        try:
            target = target.resolve()
        except OSError:
            raw_data_ok = False
            raw_message = f"raw data 경로 해석 실패: {folder_raw}"
            target = None

        if target is not None:
            if not target.exists():
                raw_data_ok = False
                raw_message = "raw data 폴더를 찾을 수 없습니다."
            elif not target.is_dir():
                raw_data_ok = False
                raw_message = "raw data 경로가 디렉토리가 아닙니다."
            else:
                raw_supported_count = 0
                try:
                    for p in target.rglob("*"):
                        if (
                            p.is_file()
                            and not p.name.startswith(".")
                            and p.suffix.lower() in SUPPORTED_EXTENSIONS
                        ):
                            raw_supported_count += 1
                except OSError as e:
                    raw_data_ok = False
                    raw_message = f"raw data 폴더 스캔 실패: {e}"

                if raw_data_ok and raw_supported_count == 0:
                    raw_data_ok = False
                    raw_message = (
                        "raw data 폴더에 지원 확장자 파일(txt/md/pdf/docx/pptx)이 없습니다."
                    )

    # === 시맨틱 식별: raw data 가 어느 양식 sheet 에 가장 가까운지 자동 판별 ===
    identified: Optional[str] = None
    identified_distance: Optional[float] = None

    if folder_raw and raw_data_ok and (raw_supported_count or 0) > 0:
        try:
            from app.domains.template_rag.domain.service.chunking_service import (
                ChunkingService as _ChunkingService,
            )

            reader = FilesystemFileReader()
            files = reader.collect(folder_raw)
            sample_chunks: list[str] = []
            for f in files[:3]:
                pieces = _ChunkingService.split(
                    f.text, chunk_size=800, overlap=0
                )
                if pieces:
                    sample_chunks.append(pieces[0])
            if sample_chunks:
                sample_query = "\n\n".join(sample_chunks)
                embedder = OpenAIEmbeddingClient()
                sample_emb = await embedder.generate(sample_query[:4000])
                repo = TemplateChunkRepositoryImpl(db)
                best = await repo.identify_best_form_type(sample_emb)
                if best is not None:
                    identified, identified_distance = best
        except Exception as e:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "[/templates/identify] semantic identification failed: %s", e
            )

    ready = template_exists and (raw_data_ok if folder_raw else True)

    if form_type is not None and not template_exists:
        message = (
            f"양식 '{form_type.value}' 에 등록된 템플릿이 없습니다. "
            f"먼저 /api/v1/rag/jobs 로 ingest 하세요."
        )
    elif folder_raw and not raw_data_ok:
        message = raw_message
    elif identified is None and folder_raw:
        message = (
            "raw data 의 양식을 자동 식별하지 못했습니다. "
            "먼저 각 양식 폴더를 /api/v1/rag/jobs 로 ingest 해야 합니다."
        )
        ready = False
    else:
        parts = []
        if identified is not None:
            parts.append(f"식별된 양식: {identified}")
        elif form_type is not None:
            parts.append(f"템플릿 {chunk_count}개 청크 준비됨")
        if raw_supported_count is not None:
            parts.append(f"raw data 지원 파일 {raw_supported_count}개")
        message = (
            ", ".join(parts) + ". PPT 생성 가능."
            if parts
            else "PPT 생성 가능."
        )

    response_form_type = form_type.value if form_type is not None else (
        identified or ""
    )

    # DB 전체 청크 수 확인 (디버깅용)
    try:
        from sqlalchemy import func as _func, select as _select
        from app.domains.template_rag.infrastructure.orm.template_chunk_orm import (
            TemplateChunkOrm as _Orm,
        )

        total_r = await db.execute(
            _select(_Orm.form_type, _func.count()).group_by(_Orm.form_type)
        )
        total_by_form = {r[0]: int(r[1]) for r in total_r.all()}
    except Exception as _e:
        total_by_form = {"_error": str(_e)}

    import logging as _logging
    _log = _logging.getLogger(__name__)
    _log.info(
        "[/templates/identify] identified=%r distance=%r raw_files=%r db_chunks_by_form=%s",
        identified,
        identified_distance,
        raw_supported_count,
        total_by_form,
    )

    # 프론트가 다양한 경로(response.identified / response.template / response.data.template / response.data.identified)
    # 로 접근하므로 모두 채워서 반환한다.
    flat = {
        "form_type": response_form_type,
        "sheet": response_form_type,
        "template": response_form_type,
        "identified": identified,
        "identified_distance": identified_distance,
        "exists": template_exists,
        "chunk_count": chunk_count,
        "raw_data_folder": str(folder_raw) if folder_raw else None,
        "raw_data_supported_files": raw_supported_count,
        "ready": ready,
        "message": message,
    }
    body_out = {**flat, "success": True, "data": flat}
    _log.info("[/templates/identify] response payload=%s", body_out)
    return body_out


@router.get("/embeddings/{form_type}")
async def get_embeddings_by_form_type(
    form_type: str,
    limit: Optional[int] = Query(default=None, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """양식별 저장된 템플릿 청크 목록 반환 (embedding 벡터 자체는 제외)."""
    try:
        ft = FormType.from_string(form_type)
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))

    repo = TemplateChunkRepositoryImpl(db)
    chunks = await repo.list_by_form_type(ft.value, limit=limit)

    items = [
        {
            "id": c.id,
            "form_type": c.form_type,
            "sheet": c.form_type,
            "template": c.form_type,
            "file_name": c.file_name,
            "file_path": c.file_path,
            "file_hash": c.file_hash,
            "chunk_index": c.chunk_index,
            "chunk_text": c.chunk_text,
            "chunk_hash": c.chunk_hash,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in chunks
    ]

    flat = {
        "form_type": ft.value,
        "sheet": ft.value,
        "template": ft.value,
        "count": len(items),
        "total": len(items),
        "chunks": items,
        "items": items,
        "embeddings": items,
    }
    return {**flat, "success": True, "data": flat}


async def _create_ppt_generation_job(body: dict, db: AsyncSession) -> dict:
    """`/ppt/jobs` 로 들어온 PPT 생성 작업.

    - form_type / folder 받아 GeneratePptxFromTemplateUseCase 실행
    - 결과는 _JOBS_CACHE 에 저장해 stream/polling 으로 받을 수 있게 함
    """
    import logging as _logging

    _log = _logging.getLogger(__name__)
    _log.info(
        "[/ppt/jobs] received keys=%s",
        list(body.keys()) if isinstance(body, dict) else type(body).__name__,
    )

    if isinstance(body, dict):
        for wrapper in ("job", "data", "payload", "request"):
            inner = body.get(wrapper)
            if isinstance(inner, dict):
                body = inner
                break

    form_type_raw = _pick(
        body,
        [
            "form_type", "formType", "form", "type",
            "template", "template_type", "templateType",
            "양식", "formName",
        ],
    )
    folder_raw = _pick(
        body,
        [
            "folder", "folder_path", "folderPath", "path",
            "raw_data_folder", "rawDataFolder", "raw_data", "rawData",
            "raw_data_path", "rawDataPath",
            "폴더", "folderName", "dir", "directory",
        ],
    )

    job_id = f"PPT_{int(_dt.now().timestamp())}"

    if not form_type_raw:
        flat = _enrich_status_fields(
            {
                "job_id": job_id,
                "status": "failed",
                "folder": folder_raw,
                "message": (
                    f"form_type 이 비어 있습니다. 받은 키: "
                    f"{list(body.keys()) if isinstance(body, dict) else []}"
                ),
            },
            is_ppt=True,
        )
        out = {**flat, "success": False, "data": flat}
        _JOBS_CACHE[job_id] = out
        return out

    if not folder_raw:
        flat = _enrich_status_fields(
            {
                "job_id": job_id,
                "status": "failed",
                "form_type": form_type_raw,
                "message": "raw data 폴더(folder_path)가 비어 있습니다.",
            },
            is_ppt=True,
        )
        out = {**flat, "success": False, "data": flat}
        _JOBS_CACHE[job_id] = out
        return out

    try:
        form_type = FormType.from_string(form_type_raw)
    except ValueError as e:
        flat = _enrich_status_fields(
            {
                "job_id": job_id,
                "status": "failed",
                "form_type": form_type_raw,
                "folder": folder_raw,
                "message": str(e),
            },
            is_ppt=True,
        )
        out = {**flat, "success": False, "data": flat}
        _JOBS_CACHE[job_id] = out
        return out

    job_id = f"{form_type.value}_PPT_{int(_dt.now().timestamp())}"

    gen_request = GeneratePptxRequest(
        form_type=form_type.value,
        raw_data_dir=folder_raw,
        top_k=5,
    )
    usecase = GeneratePptxFromTemplateUseCase(
        repository=TemplateChunkRepositoryImpl(db),
        embedding=OpenAIEmbeddingClient(),
        file_reader=FilesystemFileReader(),
        pptx_generator=PptxGeneratorImpl(),
        output_dir=PPTX_OUTPUT_DIR,
        download_url_prefix="/api/v1/ppt/download",
        llm_json=OpenAILlmJsonClient(),
    )

    try:
        result = await usecase.execute(gen_request)
    except ValueError as e:
        flat = _enrich_status_fields(
            {
                "job_id": job_id,
                "status": "failed",
                "form_type": form_type.value,
                "template": form_type.value,
                "folder": folder_raw,
                "folder_path": folder_raw,
                "raw_data_folder": folder_raw,
                "sheet": form_type.value,
                "sheet_name": form_type.value,
                "message": f"PPT 생성 실패: {e}",
            },
            is_ppt=True,
        )
        out = {**flat, "success": False, "data": flat}
        _JOBS_CACHE[job_id] = out
        _log.info("[/ppt/jobs] failed job_id=%s msg=%s", job_id, flat["message"])
        return out
    except Exception as e:
        flat = _enrich_status_fields(
            {
                "job_id": job_id,
                "status": "failed",
                "form_type": form_type.value,
                "template": form_type.value,
                "folder": folder_raw,
                "folder_path": folder_raw,
                "raw_data_folder": folder_raw,
                "sheet": form_type.value,
                "sheet_name": form_type.value,
                "message": f"PPT 생성 중 예외: {e}",
            },
            is_ppt=True,
        )
        out = {**flat, "success": False, "data": flat}
        _JOBS_CACHE[job_id] = out
        _log.exception("[/ppt/jobs] exception job_id=%s", job_id)
        return out

    flat = _enrich_status_fields(
        {
            "job_id": job_id,
            "status": "completed",
            "form_type": form_type.value,
            "template": form_type.value,
            "folder": folder_raw,
            "folder_path": folder_raw,
            "raw_data_folder": folder_raw,
            "sheet": result.sheet_name,
            "sheet_name": result.sheet_name,
            "file_path": result.file_path,
            "file_name": result.file_name,
            "saved_directory": result.saved_directory,
            "download_url": result.download_url,
            "url": result.download_url,
            "pptUrl": result.download_url,
            "ppt_url": result.download_url,
            "downloadUrl": result.download_url,
            "slide_count": result.slide_count,
            "slideCount": result.slide_count,
            "files_read": result.files_read,
            "chunks_referenced": result.chunks_referenced,
            "message": (
                f"PPT 생성 완료: {result.file_name} "
                f"(슬라이드 {result.slide_count}장)"
            ),
        },
        is_ppt=True,
    )
    out = {**flat, "success": True, "data": flat}
    _JOBS_CACHE[job_id] = out
    _log.info(
        "[/ppt/jobs] completed job_id=%s file=%s slides=%d",
        job_id, result.file_name, result.slide_count,
    )
    return out
