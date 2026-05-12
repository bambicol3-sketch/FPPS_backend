from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ValidateFolderRequest(BaseModel):
    """프론트 키 네이밍 차이를 흡수하기 위해 path / folder_path / folderPath / folder / dir 를 모두 허용."""

    model_config = ConfigDict(populate_by_name=True)

    path: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "path", "folder_path", "folderPath", "folder", "dir"
        ),
        description="검증할 폴더의 절대 경로",
    )
