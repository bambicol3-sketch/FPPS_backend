from pydantic import BaseModel


class GeneratePptxResponse(BaseModel):
    form_type: str
    sheet_name: str
    file_path: str          # 서버 내 절대 경로
    saved_directory: str    # 저장 폴더 (프론트 표시용)
    file_name: str          # 파일명 (프론트 표시용)
    download_url: str       # 실제 다운로드 엔드포인트
    slide_count: int
    files_read: int
    chunks_referenced: int
