from pydantic import BaseModel


class SheetIngestResult(BaseModel):
    form_type: str
    sheet_name: str
    folder_path: str
    files_processed: int
    files_failed: list[str]
    chunks_created: int


class IngestTemplatesResponse(BaseModel):
    sheets: list[SheetIngestResult]
    total_files_processed: int
    total_chunks_created: int
