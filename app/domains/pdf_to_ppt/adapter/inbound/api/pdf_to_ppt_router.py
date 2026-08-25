import logging
import os
import time

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from app.common.exception.app_exception import AppException
from app.common.response.base_response import BaseResponse
from app.domains.pdf_to_ppt.adapter.inbound.api.rate_limiter import enforce_rate_limit
from app.domains.pdf_to_ppt.adapter.outbound.external.openai_outline_generator_impl import (
    OpenAiOutlineGeneratorImpl,
)
from app.domains.pdf_to_ppt.adapter.outbound.file.pptx_builder_impl import (
    PptxBuilderImpl,
)
from app.domains.pdf_to_ppt.adapter.outbound.file.pypdf_text_extractor_impl import (
    PypdfTextExtractorImpl,
)
from app.domains.pdf_to_ppt.application.request.convert_pdf_request import (
    ConvertPdfRequest,
)
from app.domains.pdf_to_ppt.application.response.convert_pdf_response import (
    ConvertPdfResponse,
)
from app.domains.pdf_to_ppt.application.usecase.convert_pdf_to_ppt_usecase import (
    ConvertPdfToPptUseCase,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdf-to-ppt", tags=["pdf-to-ppt"])

OUTPUT_DIR = os.path.abspath(os.path.join(os.getcwd(), "generated_pdf_to_ppt"))
DOWNLOAD_URL_PREFIX = "/api/v1/pdf-to-ppt/download"

MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB
_GENERATED_FILE_TTL_SECONDS = 2 * 60 * 60  # 2시간 후 자동 삭제 (best-effort)


def _cleanup_expired_files() -> None:
    if not os.path.isdir(OUTPUT_DIR):
        return
    now = time.time()
    try:
        for name in os.listdir(OUTPUT_DIR):
            path = os.path.join(OUTPUT_DIR, name)
            try:
                if os.path.isfile(path) and now - os.path.getmtime(path) > _GENERATED_FILE_TTL_SECONDS:
                    os.remove(path)
            except OSError:
                continue
    except OSError as e:
        logger.warning("[pdf-to-ppt] 만료 파일 정리 실패: %s", e)


@router.post("/convert", response_model=BaseResponse[ConvertPdfResponse])
async def convert_pdf_to_ppt(
    file: UploadFile = File(...),
    _rate_limit: None = Depends(enforce_rate_limit),
):
    """PDF 업로드 → 자동 PPT 생성. 인증 불필요 (퍼블릭 셀프서비스)."""
    _cleanup_expired_files()

    if not (file.filename or "").lower().endswith(".pdf"):
        raise AppException(status_code=400, message="PDF 파일만 업로드할 수 있습니다.")

    content = await file.read()
    if not content:
        raise AppException(status_code=400, message="빈 파일입니다.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise AppException(
            status_code=413,
            message=f"파일 크기가 너무 큽니다 (최대 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB).",
        )

    usecase = ConvertPdfToPptUseCase(
        text_extractor=PypdfTextExtractorImpl(),
        outline_generator=OpenAiOutlineGeneratorImpl(),
        pptx_builder=PptxBuilderImpl(),
        output_dir=OUTPUT_DIR,
        download_url_prefix=DOWNLOAD_URL_PREFIX,
    )

    try:
        result = await usecase.execute(
            ConvertPdfRequest(
                file_bytes=content,
                file_name=file.filename or "presentation.pdf",
            )
        )
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))

    return BaseResponse.ok(data=result, message="PPT 생성이 완료되었습니다.")


@router.get("/download/{file_name}")
async def download_generated_pptx(file_name: str):
    safe_name = os.path.basename(file_name)
    file_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.isfile(file_path):
        raise AppException(
            status_code=404, message=f"파일이 존재하지 않습니다: {file_name}"
        )
    return FileResponse(
        file_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        filename=safe_name,
    )
