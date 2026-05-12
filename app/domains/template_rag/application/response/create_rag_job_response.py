from pydantic import BaseModel


class CreateRagJobResponse(BaseModel):
    job_id: str
    status: str               # "completed" | "partial" | "failed"
    form_type: str            # 화면 표시: 양식
    folder: str               # 화면 표시: 폴더
    sheet: str                # 화면 표시: 시트
    files_processed: int
    files_failed: list[str]
    chunks_created: int
    message: str              # 화면 표시: 메시지
