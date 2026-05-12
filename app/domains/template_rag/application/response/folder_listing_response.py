from typing import List, Optional

from pydantic import BaseModel


class FolderEntry(BaseModel):
    name: str
    is_directory: bool
    full_path: str


class FolderListingResponse(BaseModel):
    path: str
    parent: Optional[str]
    entries: List[FolderEntry]
