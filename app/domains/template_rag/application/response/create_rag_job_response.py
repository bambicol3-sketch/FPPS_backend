from pydantic import BaseModel


class FailedFileDetail(BaseModel):
    path: str
    reason: str


class CreateRagJobResponse(BaseModel):
    job_id: str
    status: str                            # "completed" | "partial" | "failed"
    form_type: str                         # 화면 표시: 양식
    folder: str                            # 화면 표시: 폴더
    sheet: str                             # 화면 표시: 시트
    files_processed: int
    files_failed: list[str]                # 기존 호환: 경로 목록
    failed_files: list[FailedFileDetail] = []  # 상세: 경로 + 사유
    chunks_created: int
    message: str                           # 화면 표시: 메시지
