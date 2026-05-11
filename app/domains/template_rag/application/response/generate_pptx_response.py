from pydantic import BaseModel


class GeneratePptxResponse(BaseModel):
    form_type: str
    sheet_name: str
    file_path: str
    download_url: str
    slide_count: int
    files_read: int
    chunks_referenced: int
