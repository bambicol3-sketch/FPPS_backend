from pydantic import BaseModel


class ValidateFolderResponse(BaseModel):
    path: str
    exists: bool
    is_directory: bool
    supported_file_count: int
    total_file_count: int
    extensions_breakdown: dict[str, int]
    message: str
