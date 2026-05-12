from typing import List

from pydantic import BaseModel


class FolderSearchResponse(BaseModel):
    name: str
    base: str
    matches: List[str]
    truncated: bool = False
