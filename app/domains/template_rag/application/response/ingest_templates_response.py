from pydantic import BaseModel


class FailedFile(BaseModel):
    path: str
    reason: str


class SheetIngestResult(BaseModel):
    form_type: str
    sheet_name: str
    folder_path: str
    files_processed: int
    files_failed: list[str]            # 기존 호환: 실패 파일 경로 목록
    failed_files: list[FailedFile] = []  # 상세: 경로 + 사유
    chunks_created: int


class IngestTemplatesResponse(BaseModel):
    sheets: list[SheetIngestResult]
    total_files_processed: int
    total_chunks_created: int
