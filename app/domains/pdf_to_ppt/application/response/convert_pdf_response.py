from pydantic import BaseModel


class ConvertPdfResponse(BaseModel):
    file_name: str
    download_url: str
    slide_count: int
    source_page_count: int
